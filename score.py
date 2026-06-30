"""
score.py — production scoring for the mortgage maximum-loan model.

Inference only: loads the saved 4-feature model (model_final.joblib) and scores
new applicants. Training/selection stays in 01–03; this is the handoff artifact.

Feature contract (the only inputs the model needs):
    Annual Income (USD)          float, > 0
    Credit Score                 int,   300–850
    Existing Monthly Debt (USD)  float, >= 0
    Down Payment (USD)           float, >= 0

Each scored record carries: predicted_max_loan, status (ok|rejected), reason,
model_version (hash of the artifact), scored_at (UTC). Invalid rows are rejected
with a reason — never silently coerced — and also written to a separate
<output>.rejects.csv. No business policy (approve/decline bands) is baked in;
the consuming system applies that downstream.

Importable API:
    load_model(path) -> Pipeline
    score_frame(df, model=None) -> DataFrame            # all rows + result columns
    score_record(dict, model=None) -> dict              # single record
    validate(df) -> (valid_idx, reasons_by_index)

CLI:
    python3 score.py --input applicants.csv --output scored.csv
    python3 score.py --json '{"Annual Income (USD)": 120000, "Credit Score": 740,
                                 "Existing Monthly Debt (USD)": 900, "Down Payment (USD)": 60000}'
    python3 score.py --selftest

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

MODEL_PATH = "model_final.joblib"
EXPECTED_SKLEARN = "1.6.1"  # version the artifact was trained/pickled with

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
        raise SystemExit(f"[fatal] model artifact not found: {path}")
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
# Scoring
# --------------------------------------------------------------------------- #
def score_frame(df, model=None, path=MODEL_PATH):
    """Score a frame; return every input row plus result columns.

    Raises SystemExit (fatal) if a contract *column* is absent. Per-row problems
    are reported via status='rejected' + reason, not exceptions.
    """
    missing = _missing_columns(df)
    if missing:
        raise SystemExit(f"[fatal] input is missing required column(s): {missing}")

    model = model if model is not None else load_model(path)
    ver = model_version(path)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    valid, reasons = validate(df)
    out = df.copy()
    out["predicted_max_loan"] = np.nan
    out["status"] = np.where(valid, "ok", "rejected")
    out["reason"] = reasons
    out["model_version"] = ver
    out["scored_at"] = now

    if valid.any():
        X = df.loc[valid, FEATURES].apply(pd.to_numeric, errors="coerce")
        out.loc[valid, "predicted_max_loan"] = np.round(model.predict(X), 2)

    log.info("scored %d, rejected %d (model %s)", int(valid.sum()),
             int((~valid).sum()), ver)
    return out


def score_record(record, model=None, path=MODEL_PATH):
    """Score a single applicant dict; return a result dict."""
    row = score_frame(pd.DataFrame([record]), model=model, path=path).iloc[0].to_dict()
    if pd.isna(row.get("predicted_max_loan")):
        row["predicted_max_loan"] = None
    return row


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _run_batch(args):
    try:
        df = pd.read_csv(args.input)
    except FileNotFoundError:
        raise SystemExit(f"[fatal] input file not found: {args.input}")
    if len(df) == 0:
        raise SystemExit("[fatal] input has no rows")

    scored = score_frame(df, path=args.model)
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
        raise SystemExit(f"[fatal] could not parse --json: {e}")
    if isinstance(record, list):
        raise SystemExit("[fatal] --json takes a single record object, not a list; "
                         "use --input for batches")
    print(json.dumps(score_record(record, path=args.model), default=str, indent=2))


def _run_selftest(args):
    """Smoke test: a valid row scores to a plausible number; a bad row is rejected."""
    good = {"Annual Income (USD)": 120000, "Credit Score": 740,
            "Existing Monthly Debt (USD)": 900, "Down Payment (USD)": 60000}
    bad = {"Annual Income (USD)": -5, "Credit Score": 1200,
           "Existing Monthly Debt (USD)": 900, "Down Payment (USD)": 60000}
    res = score_frame(pd.DataFrame([good, bad]), path=args.model)
    ok, rej = res.iloc[0], res.iloc[1]
    assert ok["status"] == "ok" and 0 < ok["predicted_max_loan"] < 5_000_000, ok.to_dict()
    assert rej["status"] == "rejected" and "Credit Score" in rej["reason"], rej.to_dict()
    print("selftest passed:")
    print(f"  valid  → ${ok['predicted_max_loan']:,.0f}  (model {ok['model_version']})")
    print(f"  invalid→ rejected: {rej['reason']}")


def main(argv=None):
    p = argparse.ArgumentParser(description="Score applicants with the mortgage max-loan model.")
    p.add_argument("--input", help="CSV of applicants to score (batch).")
    p.add_argument("--output", help="Where to write the scored CSV (required with --input).")
    p.add_argument("--json", help="Score a single JSON record (use '-' to read stdin).")
    p.add_argument("--model", default=MODEL_PATH, help=f"Model artifact (default: {MODEL_PATH}).")
    p.add_argument("--selftest", action="store_true", help="Run a built-in smoke test and exit.")
    p.add_argument("--quiet", action="store_true", help="Only log warnings and errors.")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.WARNING if args.quiet else logging.INFO,
                        format="%(levelname)s %(message)s")

    if args.selftest:
        return _run_selftest(args)
    if args.json is not None:
        return _run_json(args)
    if args.input:
        if not args.output:
            raise SystemExit("[fatal] --output is required with --input")
        return _run_batch(args)
    p.error("nothing to do: pass --input/--output, --json, or --selftest")


if __name__ == "__main__":
    main()
