"""
cross_examination_checks.py — Stage 5 (cross-examination) validation tasks.

Reproducible backing for CROSS_EXAMINATION.md. Runs the Chief Risk Officer
side-validation tasks against the trained model + held-out split:

  #5 over-lending tail      — how often / by how much the model sizes ABOVE the
                              bank's actual limit (the risk-bearing direction)
  #6 input sensitivity      — elasticity of the predicted limit to income & credit
  #3 debt partial-dependence— the learned shape of the debt effect (sanity check)
  #2 noise-degradation      — how fast accuracy decays as inputs get noisier

Run:  python3 scripts/cross_examination_checks.py
Reads: data/mortgage_clean.csv, models/model_final.joblib (same split/seed as 03).
"""
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error

FEATS = ["Annual Income (USD)", "Credit Score",
         "Existing Monthly Debt (USD)", "Down Payment (USD)"]
TARGET = "Max Loan Amount (USD)"
SEED = 42


def main():
    df = pd.read_csv("data/mortgage_clean.csv")
    model = joblib.load("models/model_final.joblib")
    X, y = df[FEATS], df[TARGET].values
    _, Xte, _, yte = train_test_split(X, y, test_size=0.20, random_state=SEED)
    base = model.predict(Xte)

    print("=" * 70, "\n#5 OVER-LENDING TAIL (test set, n=%d)" % len(yte))
    over = base - yte                       # >0 => model sizes ABOVE the bank limit
    om = over > 0
    op, un = over[om], -over[~om]
    pctover = over[om] / yte[om] * 100
    print(f"  above actual : {om.mean()*100:.1f}%   below: {(~om).mean()*100:.1f}%")
    print(f"  over-lend $  : mean ${op.mean():,.0f} | p95 ${np.percentile(op,95):,.0f} | max ${op.max():,.0f}")
    print(f"  over-lend %% : mean {pctover.mean():.1f}% | p95 {np.percentile(pctover,95):.1f}% | max {pctover.max():.1f}%")
    print(f"  >10%% over-lent: {(pctover>10).sum()} ({(pctover>10).sum()/len(yte)*100:.1f}% of all)")
    print(f"  cumulative notional: over ${op.sum():,.0f}  vs under ${un.sum():,.0f}")

    print("=" * 70, "\n#6 INPUT SENSITIVITY (mean %% change in predicted limit; elasticity)")
    for feat in ["Annual Income (USD)", "Credit Score"]:
        for p in (0.10, 0.20):
            for s in (1, -1):
                Xp = Xte.copy()
                Xp[feat] = Xp[feat] * (1 + s * p)
                if feat == "Credit Score":
                    Xp[feat] = Xp[feat].clip(300, 850)
                d = np.mean((model.predict(Xp) - base) / base) * 100
                print(f"  {feat.split()[0]:7s} {s*p*100:+5.0f}% -> {d:+6.2f}%  (elasticity {d/(s*p*100):.2f})")

    print("=" * 70, "\n#3 DEBT PARTIAL DEPENDENCE (set debt=v for all rows -> mean limit)")
    prev = None
    for v in (0, 500, 1000, 1500, 2000, 2500, 3000, 4000, 5000):
        Xp = Xte.copy(); Xp["Existing Monthly Debt (USD)"] = v
        m = model.predict(Xp).mean()
        print(f"  debt ${v:>5} -> ${m:,.0f}" + ("" if prev is None else f"  ({m-prev:+,.0f})"))
        prev = m

    print("=" * 70, "\n#2 NOISE-DEGRADATION (Gaussian noise = k x feature-std on all inputs)")
    print(f"  baseline      : R2={r2_score(yte,base):.4f}  MAE=${mean_absolute_error(yte,base):,.0f}")
    rng = np.random.default_rng(0)
    sd = {c: Xte[c].std() for c in FEATS}
    for k in (0.05, 0.10, 0.20, 0.50):
        Xn = Xte.copy()
        for c in FEATS:
            Xn[c] = Xn[c] + rng.normal(0, k * sd[c], len(Xn))
        Xn["Credit Score"] = Xn["Credit Score"].clip(300, 850)
        Xn["Annual Income (USD)"] = Xn["Annual Income (USD)"].clip(1, None)
        pn = model.predict(Xn)
        print(f"  noise {k*100:4.0f}%std : R2={r2_score(yte,pn):.4f}  MAE=${mean_absolute_error(yte,pn):,.0f}"
              f"  (+{mean_absolute_error(yte,pn)/mean_absolute_error(yte,base)-1:.0%})")


if __name__ == "__main__":
    main()
