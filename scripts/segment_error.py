"""
segment_error.py — error breakdown by income and credit-score band.

Additive to the closed pipeline (01–05 are NOT modified). It re-uses the held-out
predictions already written by 03_train_evaluate.py (predictions_test.csv) and
breaks the primary model's error down by APPLICANT segment — annual income and
credit score — following exactly the logic of error_by_band.csv (which bands by
loan size). Same metrics, same schema: n, segment mean, mean actual loan, MAE,
MAPE.

predictions_test.csv holds only actual/predicted/residual (the target was held
out; income and credit score are not in it). They are recovered by replaying the
SAME deterministic train/test split as 03 (seed 42, test_size 0.20): the
reconstructed test target is asserted bit-identical to predictions_test.csv's
`actual` column, which positionally confirms the join before any banding.

Bands (fixed, interpretable — mirroring error_by_band.csv, not quantiles):
  Income       : <$60k, $60–90k, $90–120k, $120–150k, $150–180k, ≥$180k
  Credit Score : standard FICO tiers — Poor <580, Fair 580–669, Good 670–739,
                 Very Good 740–799, Exceptional 800–850 (Poor is empty here: the
                 model never saw a score below 580 — see models/training_distribution.json).

    python3 scripts/segment_error.py     # -> metrics/error_by_income_band.csv, metrics/error_by_credit_band.csv

Outputs parallel error_by_band.csv. No model is loaded; no artifact is retrained.
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

CLEAN = "data/mortgage_clean.csv"
PREDICTIONS = "metrics/predictions_test.csv"
TARGET = "Max Loan Amount (USD)"
SEED = 42
TEST_SIZE = 0.20

# Same feature list / order as 03_train_evaluate.py's PRIMARY split.
PRIMARY_NUM = ["Annual Income (USD)", "Credit Score",
               "Existing Monthly Debt (USD)", "Down Payment (USD)"]

INCOME_BINS = [0, 60e3, 90e3, 120e3, 150e3, 180e3, np.inf]
INCOME_LABELS = ["<$60k", "$60-90k", "$90-120k", "$120-150k", "$150-180k", ">=$180k"]

# FICO tiers. Half-integer edges so integer scores land unambiguously; lowest
# edge 299.5 keeps the contract floor (300) in "Poor".
CREDIT_BINS = [299.5, 579.5, 669.5, 739.5, 799.5, 850.5]
CREDIT_LABELS = ["Poor <580", "Fair 580-669", "Good 670-739",
                 "Very Good 740-799", "Exceptional 800-850"]


def load_aligned():
    """Recover the test-set income & credit score and align them to the saved
    predictions, replaying 03's split. Asserts the alignment before returning."""
    df = pd.read_csv(CLEAN)
    y = df[TARGET].values
    _Xtr, Xte, _ytr, yte = train_test_split(
        df[PRIMARY_NUM], y, test_size=TEST_SIZE, random_state=SEED)

    pred = pd.read_csv(PREDICTIONS)
    if len(pred) != len(yte):
        raise SystemExit(f"row mismatch: {PREDICTIONS} has {len(pred)}, "
                         f"reconstructed test set has {len(yte)}")

    # AUDIT: the reconstructed target must equal predictions_test.csv's `actual`
    # exactly — this is what licenses the positional join of income/credit.
    max_diff = float(np.max(np.abs(np.asarray(yte) - pred["actual"].values)))
    if max_diff != 0.0:
        raise SystemExit(f"split mismatch: actual differs by up to {max_diff} — "
                         "income/credit cannot be safely joined to predictions")

    ev = Xte.reset_index(drop=True)
    ev = ev.assign(actual=pred["actual"].values,
                   predicted=pred["predicted"].values,
                   residual=pred["residual"].values)
    ev["abs_err"] = ev["residual"].abs()
    ev["ape"] = (ev["residual"].abs() / ev["actual"]) * 100
    print(f"Aligned {len(ev)} held-out rows to {PREDICTIONS} "
          f"(actual matches exactly, max abs diff = {max_diff}).")
    return ev


def error_by(ev, value_col, bins, labels, right, seg_mean_name, out_path):
    """Mirror error_by_band.csv: group the held-out rows into fixed bands of
    `value_col` and report n, segment mean, mean actual loan, MAE, MAPE."""
    band = pd.cut(ev[value_col], bins=bins, labels=labels, right=right)
    g = pd.DataFrame({"band": band, value_col: ev[value_col], "actual": ev["actual"],
                      "abs_err": ev["abs_err"], "ape": ev["ape"]})
    by_band = g.groupby("band", observed=False).agg(
        n=("actual", "size"),
        **{seg_mean_name: (value_col, "mean")},
        mean_actual=("actual", "mean"),
        MAE=("abs_err", "mean"),
        MAPE_pct=("ape", "mean")).round(2)
    by_band.to_csv(out_path)
    return by_band


def main():
    ev = load_aligned()

    inc = error_by(ev, "Annual Income (USD)", INCOME_BINS, INCOME_LABELS,
                   right=False, seg_mean_name="mean_income",
                   out_path="metrics/error_by_income_band.csv")
    print("\nError by income band (held-out test set):")
    print(inc.to_string())

    cred = error_by(ev, "Credit Score", CREDIT_BINS, CREDIT_LABELS,
                    right=True, seg_mean_name="mean_credit",
                    out_path="metrics/error_by_credit_band.csv")
    print("\nError by credit-score band (FICO tiers, held-out test set):")
    print(cred.to_string())

    # Reconcile: every band partition must cover all held-out rows.
    for name, tbl in [("income", inc), ("credit", cred)]:
        assert int(tbl["n"].sum()) == len(ev), f"{name} bands drop rows"
    print(f"\nReconciled: income and credit bands each cover all {len(ev)} rows.")
    print("Wrote metrics/error_by_income_band.csv, metrics/error_by_credit_band.csv")


if __name__ == "__main__":
    main()
