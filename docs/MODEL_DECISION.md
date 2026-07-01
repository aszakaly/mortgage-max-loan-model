# Model decision record — maximum loan amount

This document records **what was decided and on what evidence** for the mortgage
max-loan model, so every choice is auditable. It is generated/validated by the
numbered scripts (`02_model_benchmark.py`, `03_train_evaluate.py`); the tables
below are reproducible from them.

The target — `Max Loan Amount (USD)` — was **held out of all modelling** and
used only for the final evaluation in this document.

---

## 1. Feature decisions

| Feature | Decision | Basis |
|---|---|---|
| **Interest Rate** | **Excluded** (stated assumption) | **Assumption — not verifiable from this data:** the rate is treated as *calculated in parallel with the maximum loan amount* (a bank **output**, not an applicant input). This can't be fact-checked here, but it is consistent with the evidence — almost perfectly determined by credit score (r = −0.95) and predicted from other applicant inputs at **CV R² = 0.91–0.94** — on which basis using it would be circular (a bank decision predicting another) and largely re-encodes credit score. |
| **Down Payment** | **Kept** | A genuine applicant input (household purchasing power). Dropping it raises primary-model MAE from **$21,966 → $35,648** — it carries real, non-redundant signal. |
| Max Loan Amount | Held out | Ground truth / evaluation target only. |
| All other attributes | Available to models | Evaluated; see the parsimony finding below. |

## 2. Model family & target scale — benchmark

Three model families × raw vs log target, one 80/20 split (seed 42), all
metrics on the **same held-out test set in USD** (`model_benchmark.csv`):

| Model | Target | Test R² | Test MAE | Test RMSE | Test MAPE | CV R² (±std) |
|---|---|---|---|---|---|---|
| **HistGradientBoosting** | **raw** | **0.9894** | **$22,428** | **$31,937** | **3.74%** | 0.9886 (±0.0004) |
| HistGradientBoosting | log | 0.9894 | $22,463 | $31,915 | 3.70% | 0.9886 (±0.0003) |
| Random Forest | raw | 0.9876 | $24,312 | $34,498 | 4.14% | 0.9872 (±0.0003) |
| Random Forest | log | 0.9876 | $24,427 | $34,551 | 4.12% | 0.9871 (±0.0003) |
| Ridge (linear) | raw | 0.9502 | $51,858 | $69,239 | 12.11% | 0.9506 (±0.0007) |
| Ridge (linear) | log | 0.8830 | $62,625 | $106,103 | 9.97% | 0.8790 (±0.0148) |

**Decision: HistGradientBoosting on the raw target.** Basis:
- Tree ensembles beat linear decisively (R² 0.989 vs 0.95; MAE $22k vs $52k) —
  the relationship has non-linearities a linear model can't capture.
- HGB consistently edges Random Forest and trains faster.
- Raw vs log is immaterial for the winner (identical to 4 dp); raw keeps
  everything in native USD with no back-transform.
- CV R² std ≤ 0.0004 → stable, no overfitting.

## 3. Parsimony finding — the model needs only 4 features

Permutation importance on the full 12-feature model showed **8 features at ~0
importance**. A model on just **Income, Credit Score, Existing Monthly Debt,
Down Payment** matches/beats the full model:

| Model | Test R² | Test MAE | Test RMSE | Test MAPE |
|---|---|---|---|---|
| **Primary — 4 features** | **0.9897** | **$21,966** | **$31,437** | **3.65%** |
| Full — 12 features | 0.9894 | $22,428 | $31,937 | 3.74% |
| 3 features (drop Down Payment) | 0.9768 | $35,648 | — | — |

**Why the other features vanish:** they are downstream correlates of income and
credit score, carrying no independent signal once those are present —
- Job ≈ income tier: Doctor/Lawyer/Business Owner ≈ $146k, Banker/SWE/Sales ≈
  $125k, others ≈ $105k (the exact "loan tiers" seen in EDA).
- Education tracks income (HS $106k → PhD $136k).
- Age and Employment Years are 0.97 correlated; both track credit score; Loans
  Repaid correlates with credit score (0.43).

**Decision (user): ship the 4-feature model as primary; keep the full model on
record.** The primary model is simpler, marginally more accurate, easier to
govern, and uses **no demographic features** (Gender/marital status), which is
desirable for fair-lending (ECOA) defensibility.

Permutation importance, primary model (drop in R² when shuffled):
`Annual Income 1.44 · Credit Score 0.65 · Existing Monthly Debt 0.34 · Down Payment 0.03`.

## 4. Final evaluation vs the held-out actual (primary model)

Test set n = 9,998 applicants (never seen in training):

- **R² = 0.9897 · MAE = $21,966 · RMSE = $31,437 · MAPE = 3.65%**
- **72.9%** of applicants predicted within **±5%** of the bank's actual max loan;
  **94.9%** within **±10%**.

Accuracy by loan-size band (`error_by_band.csv`):

| Band | n | Mean actual | MAE | MAPE |
|---|---|---|---|---|
| <$250k | 687 | $182,907 | $9,164 | 5.60% |
| $250–500k | 2,741 | $386,253 | $15,428 | 4.00% |
| $500–750k | 2,973 | $619,497 | $23,246 | 3.76% |
| $750k–1M | 2,132 | $864,220 | $27,583 | 3.21% |
| $1–1.5M | 1,375 | $1,168,514 | $29,123 | 2.52% |
| >$1.5M | 90 | $1,640,102 | $34,136 | 2.06% |

Absolute error grows with loan size but **percentage error shrinks** — the model
is proportionally most accurate on the largest loans and slightly less precise
(in % terms) on the smallest. No band is a blind spot.

## 5. Reproduce

```
python3 01_clean_data.py        # clean + audit
python3 02_model_benchmark.py   # the §2 comparison table -> model_benchmark.csv
python3 03_train_evaluate.py    # §3–4 final models + metrics + artifacts
```
