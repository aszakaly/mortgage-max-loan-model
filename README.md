# Mortgage Maximum-Loan Model

Predicting the **maximum loan amount a bank should responsibly offer** a mortgage
applicant, from their financial profile alone — on the *mortgage_loan_dataset*
(49,990 applicants) — and validating the prediction against the bank's actual
decisions, which are held out of all modelling.

---

## Purpose

Give underwriting a consistent, explainable **first-pass loan limit** for every
applicant, and quantify how closely a model can reproduce the bank's existing
decisions.

The headline finding: a gradient-boosting model predicts the maximum loan with
**R² = 0.990 and a typical error of ±$21,966 (MAPE 3.65%)** on applicants it
never saw — placing **94.9% of them within ±10%** of the bank's actual limit —
using just **four financial inputs** (annual income, credit score, existing
monthly debt, down payment) and **no demographic data**.

> **The held-out rule:** `Max Loan Amount (USD)` — the ground truth — is excluded
> from every cleaning, feature, training and selection step. It is used **only**
> for the final evaluation in this repo.

---

## Key steps

1. **Data discovery** — profile the raw CSV: 49,990 applicants × 14 columns, one
   row per applicant; no missing values, no duplicates; 8 numeric + 5 categorical
   features + 1 target. Income, credit score and (negatively) interest rate
   correlate most with the target.
2. **Data cleaning** — `01_clean_data.py` → `mortgage_clean.csv` + a full
   integrity audit (`cleaning_audit.csv`). Nothing removed; the only anomaly (41
   rows implying a working start age < 16) is **kept and flagged**.
3. **Feature decisions** — exclude **interest rate** (assumed — not verifiable
   here — to be set *in parallel* with the loan; ~−0.95 correlated with credit
   score and 91–94% predictable from other inputs, so using it would be
   circular); **keep down payment** (a genuine input; dropping it raises error by
   62%).
4. **Method selection** — `02_model_benchmark.py` → benchmark 3 model families ×
   raw/log target (6 combinations) on one held-out split → `model_benchmark.csv`.
   Gradient boosting on the raw target wins clearly.
5. **Finalize + validate** — `03_train_evaluate.py` → fit the chosen model on a
   **4-feature** set (primary) and the full 12-feature set (on record), evaluate
   both against the held-out actual, and write metrics, error-by-band, importance
   and predictions.
6. **Presentations** — `04_build_presentations.js` (PPTX) and
   `05_build_html_decks.py` (HTML) → two audiences (executive + internal), in the
   "structured craft" brand.
7. **Production scoring** — `score.py` → inference-only handoff: loads
   `model_final.joblib`, enforces the four-feature contract, and scores CSV
   batches or a single JSON record, **rejecting out-of-range rows with a reason**.

The full evidence trail for steps 3–5 is in **`MODEL_DECISION.md`**.

---

## Key decisions

| Stage | Decision | Choice made | Why |
|---|---|---|---|
| Stage 0 – Setup | **Target leakage** | `Max Loan Amount` held out of all modelling; used only for final evaluation | The model must predict the limit, not be told it |
| Stage 2 – Cleaning | **41 anomalous rows** | **Kept and flagged** (implied working start age 14–15) | Cosmetic synthetic-data artifact (off by 1–2 yrs), 0.08% of rows; removing adds no value |
| Stage 3 – Method | **Interest rate** | **Excluded** as a predictor (on a stated assumption) | **Assumption — not verifiable from this data:** I judged the rate to be *calculated in parallel with the maximum loan amount* (a bank output, not an applicant input). It can't be fact-checked here, but it's consistent with the evidence — ~−0.95 correlation with credit score and 91–94% predictable from the other inputs — on which basis using it would be circular and redundant |
| Stage 3 – Method | **Down payment** | **Kept** | A genuine applicant input (purchasing power); dropping it raises MAE from $21,966 → $35,648 |
| Stage 3 – Method | **Model family** | **HistGradientBoosting** | Beats random forest and linear on every metric (linear leaves ~$30k MAE on the table) |
| Stage 3 – Method | **Target scale** | **Raw** (not log) | Identical accuracy for the winner; raw keeps everything in native USD |
| Stage 3 – Method | **Feature set** | **4 features** primary (income, credit, debt, down payment); full 12 kept on record | The other 8 are downstream correlates of income/credit (job ≈ income tiers, etc.) — zero permutation importance; 4-feature is marginally more accurate, simpler, and uses no demographics (ECOA-friendly) |
| Stage 3 – Method | **Evaluation** | 80/20 hold-out + 5-fold CV; R², MAE, RMSE, MAPE, error-by-band | Honest test on unseen applicants; CV confirms stability (R² std ≤ 0.0004) |
| Stage 4 – Outputs | **Deliverable** | Two decks (exec + internal) × PPTX + self-contained HTML | Separate audiences; PPTX uses Office-safe fonts, HTML uses the real brand fonts |
| Stage 4 – Outputs | **Production interface** | `score.py` — importable core (`score_frame`/`score_record`) + CLI, inference-only on `model_final.joblib` | One code path for CLI/future API; training stays in the numbered scripts; named plainly (outside the `01–05` reproduce chain, and importable) |
| Stage 4 – Outputs | **Scoring I/O** | CSV batch (rows + prediction columns) and a single JSON record | Covers scheduled batch scoring and ad-hoc/one-off requests |
| Stage 4 – Outputs | **Input validation** | Reject bad rows with a reason (missing *column* = fatal); never coerce | Lending data — surface problems, don't hide them; valid rows still score, rejects written to a separate file |
| Stage 4 – Outputs | **Scoring output** | `predicted_max_loan` + `model_version` (artifact hash) + `scored_at` + `status`; no approve/decline policy baked in | Every prediction is traceable/auditable; the consuming system owns business policy |
| Stage 4 – Outputs | **Observability** | Logs to stderr (+ optional `--log-file`); fatals raise a catchable `ScoringError`, logged at ERROR, exit 2 | Operable in production and library-friendly; per-row rejections travel with the data, not the log |

---

## Pipeline

```
mortgage_loan_dataset.csv
   │  01_clean_data.py
   ▼
mortgage_clean.csv ──► cleaning_audit.csv,  eda_summary.json
   │  02_model_benchmark.py
   ▼
model_benchmark.csv          (6 model × scale combos → choose GBM/raw)
   │  03_train_evaluate.py    (brings in the held-out target)
   ▼
model_final.joblib (+ model_full.joblib)
evaluation_metrics.json, error_by_band.csv, feature_importance.csv,
predictions_test.csv, model_eval.json
   │  gen_chart_images.py ──► img_scatter.png
   │
   ├─ 04_build_presentations.js ─► mortgage_exec_deck.pptx, mortgage_internal_deck.pptx
   └─ 05_build_html_decks.py    ─► mortgage_exec_deck.html, mortgage_internal_deck.html
```

Run order:

```bash
python3 01_clean_data.py        # → mortgage_clean.csv, cleaning_audit.csv, eda_summary.json
python3 02_model_benchmark.py   # → model_benchmark.csv (the 6-way comparison)
python3 03_train_evaluate.py    # → model_final/full.joblib, evaluation_metrics.json, ...
python3 gen_chart_images.py     # → img_scatter.png (used by the PPTX decks)
NODE_PATH=$(npm root -g) node 04_build_presentations.js   # → both .pptx decks
python3 05_build_html_decks.py  # → both .html decks
```

**Requirements:** Python 3 (`pandas`, `numpy`, `scikit-learn`, `matplotlib`,
`joblib`) and Node.js (`pptxgenjs`, install globally with `npm i -g pptxgenjs`).
LibreOffice + Poppler are only needed to *render* PPTX to images for QA, not to
produce the deliverables. `mortgage_loan_dataset.csv` is the committed raw input
(source: [Kaggle — chukwuemeka64/mortgage-data](https://www.kaggle.com/datasets/chukwuemeka64/mortgage-data)).

---

## Scoring new applicants (production)

`score.py` is the inference-only handoff artifact (not part of the reproduce
chain) — it loads `model_final.joblib` and scores new applicants, enforcing the
four-feature contract and **rejecting out-of-range rows with a reason** (never
coercing). Each record carries `predicted_max_loan` + `model_version` +
`scored_at` + a validation `status`; no approve/decline policy is baked in.

```bash
# batch: CSV in → CSV out (+ a .rejects.csv listing any invalid rows)
python3 score.py --input applicants.csv --output scored.csv

# single record
python3 score.py --json '{"Annual Income (USD)": 120000, "Credit Score": 740, "Existing Monthly Debt (USD)": 900, "Down Payment (USD)": 60000}'

python3 score.py --selftest      # built-in smoke test
```

Importable: `from score import score_frame, score_record`. Requires the same
scikit-learn the model was trained with (pinned as `EXPECTED_SKLEARN` in the
script; it warns on mismatch).

**Out-of-distribution (OOD) flag.** The contract ranges above are wider than the
data the model trained on (it never saw a credit score below 580 or a down payment
under $5,000). Every scored row also carries `ood_flag` / `ood_reason`: a **soft**
signal — it never rejects the row or changes `status` — raised when any input
falls outside the per-feature training envelope `[p1, p99]`. The bounds live in
`training_distribution.json` (rebuild with `python3 build_training_distribution.py`);
if that file is absent `ood_flag` is left empty, and `--no-ood` skips the check.

---

## Add-on analyses (post-close)

Two additive analyses layered on the closed pipeline **without modifying scripts
`01`–`05` or the model**.

**1. Segment error breakdown.** `segment_error.py` breaks the held-out error down
by applicant **income** and **credit-score** band, mirroring `error_by_band.csv`
(same metrics: n, segment mean, mean actual, MAE, MAPE). `predictions_test.csv`
holds only actual/predicted/residual, so income and credit score are recovered by
replaying `03`'s deterministic split (seed 42); the reconstructed target is
asserted **bit-identical** to the saved `actual` before any join — the alignment
is audited, not assumed. Outputs `error_by_income_band.csv` (fixed round bands)
and `error_by_credit_band.csv` (standard FICO tiers). Findings: percentage error
is highest on the lowest income band (`<$60k`, MAPE 6.2%) and on the `Very Good
740–799` credit tier (4.4%), lowest on `Exceptional 800–850` (2.4%); the `Poor
<580` tier is **empty** — the model never saw a sub-580 applicant, which is exactly
what the OOD flag guards.

**2. Out-of-distribution flag in `score.py`.** `build_training_distribution.py`
records the four inputs' training envelope `[p1, p99]` (from the same 80% the model
saw) into `training_distribution.json`; `score.py` loads it and adds the soft
`ood_flag` / `ood_reason` described above. Inputs can sit inside the valid contract
yet far outside training support — a 300 credit score or a $0 down payment passes
validation but is pure extrapolation; the flag surfaces that without blocking the
score.

Both add-ons read the pipeline's git-ignored artifacts (`mortgage_clean.csv`,
`predictions_test.csv`), so run `01` and `03` first to regenerate them.

---

## Methodology

**Model.** `HistGradientBoostingRegressor` (scikit-learn) — `max_iter=400`,
`learning_rate=0.06`, default depth — trained on the **raw** target with four
features: annual income, credit score, existing monthly debt, down payment.

**Why this model.** Six combinations (Ridge / Random Forest / HistGradientBoosting
× raw / log target) were compared on one 80/20 split, all metrics on the same
held-out test set in USD. Tree ensembles beat linear decisively (R² 0.989 vs
0.95); HistGradientBoosting edged Random Forest and trains fast; raw vs log was
immaterial for the winner. See `model_benchmark.csv`.

**Why four features.** Permutation importance on the full 12-feature model showed
8 features at ≈0 importance. A 4-feature model matches/beats the full one (R²
0.9897 vs 0.9894, MAE $21,966 vs $22,428) because job, education, age,
employment, etc. are downstream correlates of income and credit score (e.g. the
three "job tiers" exactly track income tiers). The lean model is also more
governable and uses no protected attributes.

**Validation (held-out actual).** On 9,998 unseen applicants: R² = 0.990,
MAE = $21,966, RMSE = $31,437, MAPE = 3.65%; **72.9% within ±5%** and **94.9%
within ±10%** of the actual limit. Residuals centre on zero (no systematic
over/under-lending); absolute error grows with loan size but percentage error
shrinks — most accurate on the largest loans (`error_by_band.csv`).

**Limitations.** The data is synthetic-style (cleaner and more deterministic than
a real lending book; expect lower R² in production); existing-debt's positive
correlation with the limit is likely an artifact; the model mimics the bank's
historical policy rather than judging it; collateral/LTV/affordability context is
out of scope.

---

## Files

| File | One-line description |
|---|---|
| `mortgage_loan_dataset.csv` | Raw input — 49,990 mortgage applicants × 14 columns. Source: [Kaggle — chukwuemeka64/mortgage-data](https://www.kaggle.com/datasets/chukwuemeka64/mortgage-data). |
| `01_clean_data.py` | Validates the raw data, writes the cleaned dataset + integrity audit + EDA summary. |
| `02_model_benchmark.py` | Benchmarks 6 model × target-scale combinations on one held-out split. |
| `03_train_evaluate.py` | Fits the primary (4-feature) and full (12-feature) models and evaluates both vs the held-out actual. |
| `gen_chart_images.py` | Renders the brand-styled predicted-vs-actual scatter PNG for the PPTX decks. |
| `04_build_presentations.js` | Builds the executive and internal **PPTX** decks (pptxgenjs). |
| `05_build_html_decks.py` | Builds the executive and internal **HTML** decks (Chart.js). |
| `score.py` | Production scoring (inference-only) — loads `model_final.joblib`, validates the feature contract, scores CSV batches or a JSON record, flags out-of-distribution inputs; importable core + CLI. |
| `segment_error.py` | Add-on: error breakdown by income and credit-score band (mirrors `error_by_band.csv`); audits the deterministic split alignment before joining. |
| `build_training_distribution.py` | Add-on: writes the OOD training-envelope reference (`training_distribution.json`) consumed by `score.py`. |
| `MODEL_DECISION.md` | The decision record — feature rationale, benchmark, parsimony finding, evaluation. |
| `cleaning_audit.csv` | Every integrity check + the 41 flagged-but-kept rows, with reasons; reconciles raw = kept + removed. |
| `model_benchmark.csv` | The 6-way model comparison table. |
| `evaluation_metrics.json` | Headline test metrics for both models. |
| `error_by_band.csv` | Accuracy (MAE, MAPE) by loan-size band. |
| `error_by_income_band.csv` / `error_by_credit_band.csv` | Add-on: accuracy by income band and FICO credit tier. |
| `training_distribution.json` | Add-on: the four inputs' training `[p1, p99]` envelope — the OOD reference for `score.py`. |
| `feature_importance.csv` | Permutation importance, both models. |
| `eda_summary.json` | Exploration aggregates consumed by the deck builders (regenerated by `01`). |
| `model_eval.json` | Bundle (scatter, residuals, band, importance) consumed by the deck builders. |
| `img_scatter.png` | Predicted-vs-actual scatter image embedded in the PPTX decks. |
| `mortgage_exec_deck.pptx` / `.html` | Executive briefing (≤4 content slides + appendix). |
| `mortgage_internal_deck.pptx` / `.html` | Credit & modelling deep-dive (full storyline). |
| `README.md` | This file. |

Regenerated artifacts (`mortgage_clean.csv`, `model_*.joblib`,
`predictions_test.csv`, PDF exports) are git-ignored — rebuild them by running the
pipeline above.
