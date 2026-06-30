# Cross-examination — maximum loan amount model

A pre-publish adversarial review (Stage 5 of the analytics playbook): a chosen
persona challenges the work, each challenge is recorded with a response, a
verdict, and any **side validation task** run to settle it. Numbers below are
reproducible via `cross_examination_checks.py`.

- **Reviewer persona:** Chief Risk Officer
- **Model:** `model_final.joblib` (`sha256:09a552abca85`), 4 features, raw target
- **Side tasks run on:** the held-out test set (n = 9,998) and the fitted model

---

## Challenges & verdicts

| # | Challenge (as CRO) | Response & evidence | Verdict |
|---|---|---|---|
| 1 | **It's a clone of past decisions, not a risk model.** Trained on the bank's historical limits, not realized default/affordability — it reproduces prior policy, including its errors. | True, and by design: the model optimises *agreement with past underwriting*, not loss. It cannot know whether the historical policy was itself sound. | **Open / by-design** — state as a hard caveat; gate output with affordability rules; backtest against realized outcomes if/when available. |
| 2 | **These numbers won't survive real data.** R² 0.990 on near-deterministic synthetic data says little about production. | Noise-degradation (#2): +10% input noise nearly **doubles MAE** ($21,966 → $37,471); +20% → $61,179; +50% → R² 0.67. Accuracy is genuinely fragile to noise. | **Confirmed** — expect materially lower production accuracy; a real-data backtest is mandatory before deployment. |
| 3 | **More debt → a bigger loan is backwards.** Existing debt is a top-3 driver — is the model rewarding leverage? | Partial-dependence (#3): the model uses debt in the **correct negative direction** ($0 → $903,782 down to $395,806 at $5k). The +0.275 *univariate* correlation was a confound (debt tracks income); conditionally, more debt → smaller limit. | **Resolved** — no leverage-rewarding behaviour. |
| 4 | **You're structurally blind to mortgage risk.** No LTV, DTI, property value, affordability stress, or rate/term. | Out of this dataset's scope. The predicted limit cannot be safe standalone. | **Open / scope** — never use standalone; gate with a downstream affordability/LTV check; state prominently. |
| 5 | **Show me the over-lending tail, not symmetric error.** Only over-lending is exposure. | Over-lending tail (#5): the model sizes **above** the bank's limit for **49.1%** of applicants (unbiased estimator). Over-lend tail: mean **+$22.5k**, p95 **+$68k**, max **+$255k**; **3.4%** over-lent by >10%; ~**$111M** cumulative notional over-extension on the test set (≈ matched by under-lending). | **Confirmed** — apply a conservative offset or a review band on over-predictions before any auto-approval. |
| 6 | **Income is a single point of failure** — and there's no per-decision confidence. | Sensitivity (#6): income elasticity **~1.4** (10% income → ~14% limit); **credit is even more elastic (~2.5–2.9)** — a 10% credit drop → **−29%** limit. Highly sensitive to input error/gaming. | **Confirmed** — add input-quality/fraud controls and a per-decision uncertainty / out-of-distribution flag (an OOD extrapolation flag is the natural mitigation). |

---

## Side validation tasks (run)

All reproducible with `python3 cross_examination_checks.py`:

- **#5 Over-lending tail** — 49.1% above actual; over-lend mean $22,544 / p95 $68,305 / max $255,191; 344 applicants (3.4%) over-lent >10%; cumulative notional over $110.6M vs under $109.0M.
- **#6 Input sensitivity** — income elasticity 1.35–1.40; credit elasticity 1.90–2.90 (most elastic input).
- **#3 Debt partial-dependence** — monotonically decreasing ($903,782 at $0 → $395,806 at $5k, plateauing past $4k): correct direction.
- **#2 Noise-degradation** — MAE +25% / +71% / +179% / +527% at 5 / 10 / 20 / 50% input noise.

---

## Disposition

- **Resolved:** #3 (debt direction is correct).
- **Mitigate before production:** real-data backtest (#2); downstream affordability/LTV gate (#4); conservative offset or review band on the over-lending tail (#5); input-quality/fraud controls + per-decision uncertainty / OOD flag (#6).
- **Documentation caveats:** #1 (policy-clone) and #4 (no affordability context) must be stated prominently — the model proposes a *first-pass* limit that mirrors past decisions, not a risk-validated safe limit.

No challenge blocks the analysis as delivered; together they define the conditions
for safe production use.
