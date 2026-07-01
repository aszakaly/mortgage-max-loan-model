"""
build_training_distribution.py — out-of-distribution (OOD) reference for score.py.

Additive to the closed pipeline (01–05 are NOT modified). This computes, ONCE,
the per-feature training distribution of the four model inputs and writes a small,
committable JSON reference (training_distribution.json). score.py loads it at
runtime to flag applicants whose inputs fall outside the range the model actually
learned from — so the scorer stays inference-only and needs no raw data in
production.

Why a separate artifact: the contract ranges enforced in score.py (e.g. Credit
Score 300–850, Down Payment ≥ 0) are far wider than the training support (Credit
Score 580–850, Down Payment ≥ 5,000). A row can pass validation yet sit in a
region the model never saw, where its prediction is an extrapolation. The OOD
flag surfaces exactly that — as a SOFT signal, not a rejection.

Reference matches the model's training split EXACTLY (same seed/split as
03_train_evaluate.py), so the bounds describe the data the shipped model saw.

Method: per-feature percentile envelope. For each input we store the [p1, p99]
band (the flag bounds) plus min/max/mean/std and a few extra percentiles for the
record. score.py flags a row if any input falls below p1 or above p99.

    python3 scripts/build_training_distribution.py            # -> models/training_distribution.json
    python3 scripts/build_training_distribution.py --out X.json
"""

import argparse
import hashlib
import json

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

CLEAN = "data/mortgage_clean.csv"
TARGET = "Max Loan Amount (USD)"
SEED = 42                 # identical to 02/03 — reproduces the model's train split
TEST_SIZE = 0.20

# The four model inputs, in the score.py contract order.
FEATURES = ["Annual Income (USD)", "Credit Score",
            "Existing Monthly Debt (USD)", "Down Payment (USD)"]

LOWER_PCT = 1.0           # envelope lower bound (flag below this)
UPPER_PCT = 99.0          # envelope upper bound (flag above this)
MODEL_PATH = "models/model_final.joblib"


def _model_hash(path=MODEL_PATH):
    """Short content hash of the paired model artifact (audit/traceability only —
    the distribution depends on the data split, not the model)."""
    try:
        with open(path, "rb") as f:
            return "sha256:" + hashlib.sha256(f.read()).hexdigest()[:12]
    except FileNotFoundError:
        return "unknown"


def build_reference(clean_path=CLEAN):
    """Replicate the model's 80% training split and summarise each input."""
    df = pd.read_csv(clean_path)
    y = df[TARGET].values
    # Same call signature/order as 03_train_evaluate.py -> identical Xtr rows.
    Xtr, _Xte, _ytr, _yte = train_test_split(
        df[FEATURES], y, test_size=TEST_SIZE, random_state=SEED)

    feats = {}
    for col in FEATURES:
        s = Xtr[col].astype(float)
        q = s.quantile([0.005, LOWER_PCT / 100, 0.05, 0.25, 0.5,
                        0.75, 0.95, UPPER_PCT / 100, 0.995])
        feats[col] = {
            "p_low": float(q[LOWER_PCT / 100]),    # flag bound (lower)
            "p_high": float(q[UPPER_PCT / 100]),   # flag bound (upper)
            "min": float(s.min()), "max": float(s.max()),
            "mean": float(s.mean()), "std": float(s.std()),
            "p0.5": float(q[0.005]), "p5": float(q[0.05]), "p25": float(q[0.25]),
            "p50": float(q[0.5]), "p75": float(q[0.75]), "p95": float(q[0.95]),
            "p99.5": float(q[0.995]),
        }

    return {
        "method": "per_feature_percentile_envelope",
        "lower_percentile": LOWER_PCT,
        "upper_percentile": UPPER_PCT,
        "n_train": int(len(Xtr)),
        "source": (f"{clean_path} training split "
                   f"(random_state={SEED}, test_size={TEST_SIZE}) — "
                   "the 80% the shipped model was fit on"),
        "paired_model": _model_hash(),
        "note": ("Soft OOD flag: a row is flagged if any input is < p_low or "
                 "> p_high. ~1% of training sits beyond each bound by construction."),
        "features": feats,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Build the OOD training-distribution reference for score.py.")
    p.add_argument("--clean", default=CLEAN, help=f"Cleaned dataset (default: {CLEAN}).")
    p.add_argument("--out", default="models/training_distribution.json", help="Output JSON path.")
    args = p.parse_args(argv)

    ref = build_reference(args.clean)
    with open(args.out, "w") as f:
        json.dump(ref, f, indent=2)

    print(f"Wrote {args.out}  (n_train={ref['n_train']}, paired_model={ref['paired_model']})")
    print(f"Envelope = [p{ref['lower_percentile']:g}, p{ref['upper_percentile']:g}] per feature:")
    for col, d in ref["features"].items():
        print(f"  {col:<28} flag if <{d['p_low']:.2f} or >{d['p_high']:.2f}   "
              f"(seen min={d['min']:.2f}, max={d['max']:.2f})")


if __name__ == "__main__":
    main()
