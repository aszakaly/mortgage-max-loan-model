"""
01_clean_data.py — Mortgage max-loan project, Stage 2 (cleaning + audit).

Input : data/mortgage_loan_dataset.csv  (raw, 49,990 rows)
Output: data/mortgage_clean.csv         (validated dataset)
        metrics/cleaning_audit.csv      (every check + every flagged row, with reasons)

Cleaning policy (decided with the user):
  - The raw data has no nulls, no duplicates, and no impossible/contradictory
    values, so NO rows are removed and NO values are altered.
  - The one anomaly found — 41 rows where Employment Years implies the person
    started working at age 14-15 (i.e. Employment Years > Age - 16) — is
    cosmetic (off by 1-2 years, 0.08% of rows) and is KEPT but FLAGGED in the
    audit, per the user's instruction.

Reconciliation guarantee: kept + removed == raw  (here: 49,990 + 0 == 49,990).
"""

import json

import numpy as np
import pandas as pd

RAW = "data/mortgage_loan_dataset.csv"
CLEAN = "data/mortgage_clean.csv"
AUDIT = "metrics/cleaning_audit.csv"
EDA = "metrics/eda_summary.json"
TARGET = "Max Loan Amount (USD)"
# Numeric predictors for the correlation panel (interest rate excluded by decision).
EDA_NUMERIC = ["Annual Income (USD)", "Credit Score", "Down Payment (USD)",
               "Employment Years", "Age", "Loans Repaid", "Existing Monthly Debt (USD)"]
EDA_CATS = ["Education", "Job", "Married", "Gender", "Area"]

NUMERIC_POSITIVE = [
    "Age", "Annual Income (USD)", "Down Payment (USD)",
    "Credit Score", "Max Loan Amount (USD)",
]
NUMERIC_NONNEG = ["Employment Years", "Existing Monthly Debt (USD)", "Loans Repaid"]
CATEGORICAL = ["Gender", "Married", "Education", "Job", "Area"]


def write_eda_summary(df):
    """Exploration aggregates consumed by the deck builders (04/05).

    Kept here so the whole pipeline is reproducible from the raw CSV: target
    distribution, correlation of numeric predictors with the target, and mean
    target by category. Interest rate is excluded from the correlation panel.
    """
    counts, edges = np.histogram(df[TARGET].dropna(), bins=30)
    corr = {c: round(float(df[c].corr(df[TARGET])), 3) for c in EDA_NUMERIC}
    corr = dict(sorted(corr.items(), key=lambda kv: abs(kv[1]), reverse=True))
    cat_target = {}
    for c in EDA_CATS:
        g = df.groupby(c)[TARGET].agg(["mean", "count"]).sort_values("mean")
        cat_target[c] = {"labels": g.index.tolist(),
                         "means": [round(float(x), 0) for x in g["mean"]],
                         "counts": [int(x) for x in g["count"]]}
    out = {
        "target_hist": {"counts": counts.tolist(), "edges": [round(float(x), 2) for x in edges]},
        "corr": corr, "cat_target": cat_target, "n": int(len(df)),
    }
    json.dump(out, open(EDA, "w"))


def main():
    df = pd.read_csv(RAW)
    raw_n = len(df)
    audit_rows = []  # one record per integrity check (count of offending rows)

    def check(step, description, mask):
        n = int(mask.sum())
        audit_rows.append({
            "step": step,
            "check": description,
            "rows_flagged": n,
            "action": "removed" if False else "kept",  # nothing is removed here
        })
        return n

    # --- Integrity checks (none of these should remove rows) ---
    check("C1", "Duplicate rows", df.duplicated())
    check("C2", "Any null value in row", df.isna().any(axis=1))
    for c in NUMERIC_POSITIVE:
        check("C3", f"{c} <= 0", df[c] <= 0)
    for c in NUMERIC_NONNEG:
        check("C4", f"{c} < 0", df[c] < 0)
    check("C5", "Credit Score outside 300-850",
          (df["Credit Score"] < 300) | (df["Credit Score"] > 850))
    check("C6", "Down Payment > Max Loan Amount",
          df["Down Payment (USD)"] > df["Max Loan Amount (USD)"])
    check("C7", "Annualised existing debt > Annual income",
          df["Existing Monthly Debt (USD)"] * 12 > df["Annual Income (USD)"])
    for c in CATEGORICAL:
        s = df[c].astype(str)
        check("C8", f"{c} has leading/trailing whitespace", s != s.str.strip())

    # --- The one real anomaly: implausibly young working start (KEPT, flagged) ---
    start_age = df["Age"] - df["Employment Years"]
    young = start_age < 16
    check("C9", "Employment Years > Age-16 (implied start age < 16) — KEPT, FLAGGED", young)

    # Per-row detail for the flagged rows, so each is individually auditable.
    flagged = df[young].copy()
    flagged.insert(0, "row_index", flagged.index)
    flagged["implied_start_age"] = start_age[young]
    flagged["audit_step"] = "C9"
    flagged["audit_reason"] = (
        "Employment Years exceeds (Age - 16); implied start age "
        + flagged["implied_start_age"].astype(str)
        + ". Cosmetic synthetic-data artifact (off by 1-2 yrs). Kept by decision."
    )

    # --- Write outputs ---
    df.to_csv(CLEAN, index=False)
    write_eda_summary(df)

    summary = pd.DataFrame(audit_rows)
    removed_n = 0
    kept_n = raw_n - removed_n

    # Audit file: a summary block of checks, then the per-row flagged detail.
    with open(AUDIT, "w") as f:
        f.write("# CLEANING AUDIT — mortgage max-loan project\n")
        f.write(f"# raw_rows={raw_n}  kept_rows={kept_n}  removed_rows={removed_n}  "
                f"reconciles={kept_n + removed_n == raw_n}\n")
        f.write("#\n# --- Integrity checks ---\n")
        summary.to_csv(f, index=False)
        f.write("#\n# --- Flagged rows kept (step C9) ---\n")
        flagged.to_csv(f, index=False)

    # --- Console report ---
    print(f"Raw rows     : {raw_n}")
    print(f"Removed rows : {removed_n}")
    print(f"Kept rows    : {kept_n}")
    print(f"Reconciles   : {kept_n + removed_n == raw_n}")
    print(f"Flagged-kept : {len(flagged)} rows (step C9)")
    print("\nIntegrity checks (rows_flagged should be 0 except C9):")
    print(summary.to_string(index=False))
    print(f"\nWrote {CLEAN} and {AUDIT}")


if __name__ == "__main__":
    main()
