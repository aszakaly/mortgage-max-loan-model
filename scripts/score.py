"""
score.py — production scoring for the mortgage maximum-loan model.

Inference only: loads the saved 4-feature model (models/model_final.joblib) and scores
new applicants. Training/selection stays in 01–03; this is the handoff artifact.

Feature contract (the only inputs the model needs):
    Annual Income (USD)          float, > 0
    Credit Score                 int,   300–850
    Existing Monthly Debt (USD)  float, >= 0
    Down Payment (USD)           float, >= 0

Each scored record carries: predicted_max_loan, status (ok|rejected), reason,
ood_flag / ood_reason (out-of-distribution signal — see below), model_version
(hash of the artifact), scored_at (UTC). Invalid rows are rejected with a reason
— never silently coerced — and also written to a separate <output>.rejects.csv.
No business policy (approve/decline bands) is baked in; the consuming system
applies that downstream.

Out-of-distribution (OOD) flag: the contract ranges above are wider than the
data the model actually trained on (e.g. it never saw a Credit Score below 580
or a Down Payment under $5,000). A row whose inputs fall outside the per-feature
training envelope [p1, p99] is flagged ood_flag=True with a per-feature
ood_reason — a SOFT signal that the prediction is an extrapolation. It does NOT
reject the row or change status; the bounds live in models/training_distribution.json
(built by scripts/build_training_distribution.py). If that file is absent, ood_flag is
left empty (unknown).

Importable API:
    load_model(path) -> Pipeline
    score_frame(df, model=None) -> DataFrame            # all rows + result columns
    score_record(dict, model=None) -> dict              # single record
    validate(df) -> (valid_idx, reasons_by_index)
    ood_check(df, dist) -> (ood_flag, ood_reason)       # out-of-distribution signal

CLI:
    python3 scripts/score.py --input applicants.csv --output scored.csv
    python3 scripts/score.py --json '{"Annual Income (USD)": 120000, "Credit Score": 740,
                                 "Existing Monthly Debt (USD)": 900, "Down Payment (USD)": 60000}'
    python3 scripts/score.py --selftest

Logging: operational + fatal messages go to stderr (add --log-file to also persist
them); per-row rejections travel with the data (reason column + .rejects.csv), not
the log. Fatal errors are logged at ERROR and exit 2.

Exit codes: 0 ok · 2 fatal (bad args / missing model / missing contract column / no input).
Requires the same scikit-learn the model was trained with (see EXPECTED_SKLEARN).
"""

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

MODEL_PATH = "models/model_final.joblib"
EXPECTED_SKLEARN = "1.6.1"  # version the artifact was trained/pickled with
DIST_PATH = "models/training_distribution.json"  # OOD reference (build_training_distribution.py)

FEATURES = ["Annual Income (USD)", "Credit Score",
            "Existing Monthly Debt (USD)", "Down Payment (USD)"]
# (min, max); None = unbounded on that side. Inclusive bounds.
RANGES = {
    "Annual Income (USD)": (0.01, None),
    "Credit Score": (300, 850),
    "Existing Monthly Debt (USD)": (0, None),
    "Down Payment (USD)": (0, None),
}

log = logging.getLogger("score")


class ScoringError(Exception):
    """A fatal, caller-facing error (bad args, missing model/contract column, bad
    input). Library code raises it; the CLI logs it at ERROR and exits with 2."""


def setup_logging(level=logging.INFO, log_file=None):
    """Operational + fatal logs go to stderr (the platform persists those);
    add a file handler too when log_file is given. Per-row rejections are NOT
    logged here — they travel with the data (reason column + .rejects.csv)."""
    handlers = [logging.StreamHandler(sys.stderr)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(level=level, force=True,
                        format="%(asctime)s %(levelname)s %(message)s", handlers=handlers)


# --------------------------------------------------------------------------- #
# Model loading
# --------------------------------------------------------------------------- #
def load_model(path=MODEL_PATH):
    """Load the fitted pipeline; warn on a scikit-learn version mismatch."""
    import joblib
    import sklearn
    if sklearn.__version__ != EXPECTED_SKLEARN:
        log.warning("scikit-learn %s differs from the trained version %s; "
                    "unpickling may be unreliable.", sklearn.__version__, EXPECTED_SKLEARN)
    try:
        model = joblib.load(path)
    except FileNotFoundError:
        raise ScoringError(f"model artifact not found: {path}")
    return model


def model_version(path=MODEL_PATH):
    """Short content hash of the artifact — identifies exactly which model scored."""
    try:
        with open(path, "rb") as f:
            return "sha256:" + hashlib.sha256(f.read()).hexdigest()[:12]
    except FileNotFoundError:
        return "unknown"


# --------------------------------------------------------------------------- #
# Validation (feature contract + ranges)
# --------------------------------------------------------------------------- #
def _missing_columns(df):
    return [c for c in FEATURES if c not in df.columns]


def validate(df):
    """Return (valid_boolean_series, reason_series) for a frame.

    A missing *column* is a contract error handled by the caller (fatal); here we
    check per-row: non-numeric / missing values and out-of-range values.
    """
    reasons = pd.Series([""] * len(df), index=df.index, dtype=object)
    for col in FEATURES:
        vals = pd.to_numeric(df[col], errors="coerce")
        lo, hi = RANGES[col]
        bad_nan = vals.isna()
        bad_lo = (~bad_nan) & (lo is not None) & (vals < lo)
        bad_hi = (~bad_nan) & (hi is not None) & (vals > hi)
        for idx in df.index[bad_nan]:
            reasons[idx] += f"{col}: missing/non-numeric; "
        for idx in df.index[bad_lo]:
            reasons[idx] += f"{col}={df.at[idx, col]}: below minimum {lo}; "
        for idx in df.index[bad_hi]:
            reasons[idx] += f"{col}={df.at[idx, col]}: above maximum {hi}; "
    valid = reasons == ""
    return valid, reasons.str.rstrip("; ")


# --------------------------------------------------------------------------- #
# Out-of-distribution (OOD) signal
# --------------------------------------------------------------------------- #
_DIST_CACHE = {}


def load_distribution(path=DIST_PATH):
    """Load the per-feature training envelope (cached). Returns None if the
    reference file is absent — OOD is then reported as unknown, not an error."""
    if path in _DIST_CACHE:
        return _DIST_CACHE[path]
    try:
        with open(path) as f:
            dist = json.load(f)
    except FileNotFoundError:
        log.warning("OOD reference %s not found; ood_flag will be empty (unknown). "
                    "Build it with build_training_distribution.py.", path)
        dist = None
    _DIST_CACHE[path] = dist
    return dist


def ood_check(df, dist):
    """Flag rows whose inputs fall outside the training envelope [p_low, p_high].

    SOFT signal: returns (ood_flag, ood_reason) and never rejects a row. ood_flag
    is a nullable boolean — pd.NA where it can't be assessed (no reference, or a
    feature that is missing/non-numeric for that row). ood_reason names each
    offending feature with its value, direction, and the breached bound.
    """
    idx = df.index
    if not dist:
        return (pd.array([pd.NA] * len(df), dtype="boolean"),
                pd.Series([""] * len(df), index=idx, dtype=object))

    plo, phi = dist["lower_percentile"], dist["upper_percentile"]
    reason = pd.Series([""] * len(df), index=idx, dtype=object)
    assessable = pd.Series(False, index=idx)
    out_any = pd.Series(False, index=idx)

    for col, b in dist["features"].items():
        if col not in df.columns:
            continue
        vals = pd.to_numeric(df[col], errors="coerce")
        present = vals.notna()
        assessable |= present
        below = present & (vals < b["p_low"])
        above = present & (vals > b["p_high"])
        out_any |= (below | above)
        for i in idx[below]:
            reason[i] += f"{col}={vals[i]:,.0f} < p{plo:g}={b['p_low']:,.0f}; "
        for i in idx[above]:
            reason[i] += f"{col}={vals[i]:,.0f} > p{phi:g}={b['p_high']:,.0f}; "

    flag = pd.array(out_any.to_numpy(), dtype="boolean")
    flag[~assessable.to_numpy()] = pd.NA   # nothing assessable -> unknown, not False
    return flag, reason.str.rstrip("; ")


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
def score_frame(df, model=None, path=MODEL_PATH, dist_path=DIST_PATH):
    """Score a frame; return every input row plus result columns.

    Raises SystemExit (fatal) if a contract *column* is absent. Per-row problems
    are reported via status='rejected' + reason, not exceptions. Out-of-range vs
    out-of-distribution are separate: validation (status/reason) is the hard
    contract; ood_flag/ood_reason is a soft signal that never blocks scoring.
    Pass dist_path=None to skip the OOD check entirely.
    """
    missing = _missing_columns(df)
    if missing:
        raise ScoringError(f"input is missing required column(s): {missing}")

    model = model if model is not None else load_model(path)
    ver = model_version(path)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    valid, reasons = validate(df)
    ood_flag, ood_reason = ood_check(df, load_distribution(dist_path) if dist_path else None)
    out = df.copy()
    out["predicted_max_loan"] = np.nan
    out["status"] = np.where(valid, "ok", "rejected")
    out["reason"] = reasons
    out["ood_flag"] = ood_flag
    out["ood_reason"] = ood_reason
    out["model_version"] = ver
    out["scored_at"] = now

    if valid.any():
        X = df.loc[valid, FEATURES].apply(pd.to_numeric, errors="coerce")
        out.loc[valid, "predicted_max_loan"] = np.round(model.predict(X), 2)

    n_ood = int((ood_flag == True).sum())  # noqa: E712 — nullable bool, count True only
    log.info("scored %d, rejected %d, out-of-distribution %d (model %s)",
             int(valid.sum()), int((~valid).sum()), n_ood, ver)
    return out


def score_record(record, model=None, path=MODEL_PATH, dist_path=DIST_PATH):
    """Score a single applicant dict; return a result dict."""
    row = score_frame(pd.DataFrame([record]), model=model, path=path,
                      dist_path=dist_path).iloc[0].to_dict()
    for k in ("predicted_max_loan", "ood_flag"):   # pd.NA -> None for clean JSON
        if pd.isna(row.get(k)):
            row[k] = None
        elif k == "ood_flag":
            row[k] = bool(row[k])
    return row


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _run_batch(args):
    try:
        df = pd.read_csv(args.input)
    except FileNotFoundError:
        raise ScoringError(f"input file not found: {args.input}")
    if len(df) == 0:
        raise ScoringError("input has no rows")

    scored = score_frame(df, path=args.model, dist_path=args.dist)
    scored.to_csv(args.output, index=False)
    rejects = scored[scored["status"] == "rejected"]
    if len(rejects):
        rej_path = args.output.rsplit(".", 1)[0] + ".rejects.csv"
        rejects.to_csv(rej_path, index=False)
        log.info("wrote %s (%d rows) and %s (%d rejected)",
                 args.output, len(scored), rej_path, len(rejects))
    else:
        log.info("wrote %s (%d rows, 0 rejected)", args.output, len(scored))


def _run_json(args):
    payload = args.json if args.json != "-" else sys.stdin.read()
    try:
        record = json.loads(payload)
    except json.JSONDecodeError as e:
        raise ScoringError(f"could not parse --json: {e}")
    if isinstance(record, list):
        raise ScoringError("--json takes a single record object, not a list; "
                           "use --input for batches")
    print(json.dumps(score_record(record, path=args.model, dist_path=args.dist),
                     default=str, indent=2))


def _run_selftest(args):
    """Smoke test: a valid row scores to a plausible number; a bad row is rejected;
    an in-contract-but-unseen row is flagged out-of-distribution (not rejected)."""
    good = {"Annual Income (USD)": 120000, "Credit Score": 740,
            "Existing Monthly Debt (USD)": 900, "Down Payment (USD)": 60000}
    bad = {"Annual Income (USD)": -5, "Credit Score": 1200,
           "Existing Monthly Debt (USD)": 900, "Down Payment (USD)": 60000}
    # Valid per the contract (Credit Score 300–850, Down Payment ≥ 0) but outside
    # the training envelope (Credit Score < p1=600, Down Payment < p1=5,000).
    ood = {"Annual Income (USD)": 120000, "Credit Score": 590,
           "Existing Monthly Debt (USD)": 900, "Down Payment (USD)": 0}
    res = score_frame(pd.DataFrame([good, bad, ood]), path=args.model, dist_path=args.dist)
    ok, rej, oo = res.iloc[0], res.iloc[1], res.iloc[2]
    assert ok["status"] == "ok" and 0 < ok["predicted_max_loan"] < 5_000_000, ok.to_dict()
    assert rej["status"] == "rejected" and "Credit Score" in rej["reason"], rej.to_dict()
    print("selftest passed:")
    print(f"  valid  → ${ok['predicted_max_loan']:,.0f}  (model {ok['model_version']})")
    print(f"  invalid→ rejected: {rej['reason']}")

    dist = load_distribution(args.dist) if args.dist else None
    if dist:
        assert ok["ood_flag"] == False, ok.to_dict()              # noqa: E712
        assert oo["status"] == "ok", oo.to_dict()                 # OOD never rejects
        assert oo["ood_flag"] == True, oo.to_dict()               # noqa: E712
        assert "Credit Score" in oo["ood_reason"] and "Down Payment" in oo["ood_reason"], oo.to_dict()
        print(f"  in-distribution → ood_flag=False")
        print(f"  out-of-distribution (still scored ${oo['predicted_max_loan']:,.0f}) → {oo['ood_reason']}")
    else:
        print("  (OOD reference unavailable — ood checks skipped)")


def main(argv=None):
    p = argparse.ArgumentParser(description="Score applicants with the mortgage max-loan model.")
    p.add_argument("--input", help="CSV of applicants to score (batch).")
    p.add_argument("--output", help="Where to write the scored CSV (required with --input).")
    p.add_argument("--json", help="Score a single JSON record (use '-' to read stdin).")
    p.add_argument("--model", default=MODEL_PATH, help=f"Model artifact (default: {MODEL_PATH}).")
    p.add_argument("--dist", default=DIST_PATH,
                   help=f"OOD training-distribution reference (default: {DIST_PATH}).")
    p.add_argument("--no-ood", action="store_true",
                   help="Skip the out-of-distribution check (ood_flag left empty).")
    p.add_argument("--selftest", action="store_true", help="Run a built-in smoke test and exit.")
    p.add_argument("--log-file", help="Also write logs to this file (stderr is always used).")
    p.add_argument("--quiet", action="store_true", help="Only log warnings and errors.")
    args = p.parse_args(argv)
    if args.no_ood:
        args.dist = None

    setup_logging(logging.WARNING if args.quiet else logging.INFO, args.log_file)

    try:
        if args.selftest:
            return _run_selftest(args)
        if args.json is not None:
            return _run_json(args)
        if args.input:
            if not args.output:
                raise ScoringError("--output is required with --input")
            return _run_batch(args)
        p.error("nothing to do: pass --input/--output, --json, or --selftest")
    except ScoringError as e:
        log.error("%s", e)
        sys.exit(2)


if __name__ == "__main__":
    main()
