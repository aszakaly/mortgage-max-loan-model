"""
03_train_evaluate.py — Mortgage max-loan project, Stage 3 (finalize + evaluate).

Trains the chosen model family (HistGradientBoosting, raw target) for TWO
feature sets and evaluates both against the HELD-OUT actual Max Loan Amount —
the only stage where the ground truth is used:

  PRIMARY (4 features): Annual Income, Credit Score, Existing Monthly Debt,
                        Down Payment. Shipped model — simpler, ECOA-friendly,
                        and marginally more accurate (see MODEL_DECISION.md).
  FULL (12 features)  : all applicant attributes; kept on record for the
                        transparency trade-off the user asked to document.

Artifacts:
  models/model_final.joblib / models/model_full.joblib   fitted pipelines (reproducible)
  metrics/evaluation_metrics.json          test metrics for BOTH models
  metrics/error_by_band.csv                primary model accuracy by loan band
  metrics/feature_importance.csv           permutation importance, BOTH models
  metrics/predictions_test.csv             actual/predicted/residual (primary)
  metrics/model_eval.json                  bundle for the report widgets

Protocol matches 02_model_benchmark.py (same split, seed).
"""

import json
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

CLEAN = "data/mortgage_clean.csv"
TARGET = "Max Loan Amount (USD)"
SEED = 42

PRIMARY_NUM = ["Annual Income (USD)", "Credit Score",
               "Existing Monthly Debt (USD)", "Down Payment (USD)"]
PRIMARY_CAT = []
FULL_CAT = ["Gender", "Married", "Education", "Job", "Area"]
FULL_NUM = ["Age", "Employment Years", "Annual Income (USD)", "Down Payment (USD)",
            "Credit Score", "Existing Monthly Debt (USD)", "Loans Repaid"]

BANDS = [0, 250e3, 500e3, 750e3, 1e6, 1.5e6, np.inf]
BAND_LABELS = ["<$250k", "$250-500k", "$500-750k", "$750k-1M", "$1-1.5M", ">$1.5M"]


def metrics(y, p):
    return {"R2": float(r2_score(y, p)), "MAE": float(mean_absolute_error(y, p)),
            "RMSE": float(np.sqrt(mean_squared_error(y, p))),
            "MAPE_%": float(np.mean(np.abs((y - p) / y)) * 100)}


def build(cats, nums):
    return Pipeline([
        ("pre", ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), cats),
                                   ("num", "passthrough", nums)])),
        ("m", HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06,
                                            random_state=SEED))])


def fit_eval(df, y, cats, nums):
    feats = cats + nums
    Xtr, Xte, ytr, yte = train_test_split(df[feats], y, test_size=0.20, random_state=SEED)
    model = build(cats, nums).fit(Xtr, ytr)
    pred = model.predict(Xte)
    pi = permutation_importance(model, Xte, yte, n_repeats=10, random_state=SEED,
                                scoring="r2", n_jobs=-1)
    imp = (pd.DataFrame({"feature": feats, "importance": pi.importances_mean,
                         "std": pi.importances_std})
           .sort_values("importance", ascending=False).reset_index(drop=True))
    return model, yte, pred, imp


def main():
    df = pd.read_csv(CLEAN)
    y = df[TARGET].values

    prim_model, yte, prim_pred, prim_imp = fit_eval(df, y, PRIMARY_CAT, PRIMARY_NUM)
    full_model, _, full_pred, full_imp = fit_eval(df, y, FULL_CAT, FULL_NUM)

    prim_m, full_m = metrics(yte, prim_pred), metrics(yte, full_pred)
    print("=== Final model comparison (same held-out test set, n=%d) ===" % len(yte))
    cmp = pd.DataFrame([
        {"model": "PRIMARY (4 feat)", **{k: round(v, 4) for k, v in prim_m.items()}},
        {"model": "FULL (12 feat)", **{k: round(v, 4) for k, v in full_m.items()}}])
    print(cmp.to_string(index=False))

    # --- Primary model: error by loan-size band ---
    resid = yte - prim_pred
    eb = pd.DataFrame({"band": pd.cut(yte, bins=BANDS, labels=BAND_LABELS),
                       "actual": yte, "abs_err": np.abs(resid), "ape": np.abs(resid / yte) * 100})
    by_band = eb.groupby("band", observed=False).agg(
        n=("actual", "size"), mean_actual=("actual", "mean"),
        MAE=("abs_err", "mean"), MAPE_pct=("ape", "mean")).round(2)
    by_band.to_csv("metrics/error_by_band.csv")
    print("\nPrimary model — error by loan-size band:")
    print(by_band.to_string())

    print("\nPrimary model — permutation importance:")
    print(prim_imp.round(4).to_string(index=False))
    print("\nFull model — permutation importance (note the 8 near-zero features):")
    print(full_imp.round(4).to_string(index=False))

    within5 = float(np.mean(np.abs(resid / yte) <= 0.05) * 100)
    within10 = float(np.mean(np.abs(resid / yte) <= 0.10) * 100)
    print(f"\nPrimary: {within5:.1f}% of applicants within +/-5%, "
          f"{within10:.1f}% within +/-10% of actual.")

    # --- Persist ---
    joblib.dump(prim_model, "models/model_final.joblib")
    joblib.dump(full_model, "models/model_full.joblib")
    prim_imp.assign(model="primary").to_csv("metrics/feature_importance.csv", index=False)
    full_imp.assign(model="full").to_csv("metrics/feature_importance.csv", mode="a",
                                         header=False, index=False)
    pd.DataFrame({"actual": yte, "predicted": prim_pred, "residual": resid}).to_csv(
        "metrics/predictions_test.csv", index=False)
    json.dump({"primary": prim_m, "full": full_m,
               "n_test": int(len(yte)), "within_5pct": within5, "within_10pct": within10},
              open("metrics/evaluation_metrics.json", "w"), indent=2)

    rng = np.random.default_rng(SEED)
    idx = rng.choice(len(yte), size=min(2500, len(yte)), replace=False)
    rh_c, rh_e = np.histogram(resid, bins=40)
    json.dump({
        "primary_metrics": prim_m, "full_metrics": full_m, "n_test": int(len(yte)),
        "within_5pct": within5, "within_10pct": within10,
        "scatter": {"actual": yte[idx].round(0).tolist(), "pred": prim_pred[idx].round(0).tolist()},
        "resid_hist": {"counts": rh_c.tolist(), "edges": [round(x) for x in rh_e.tolist()]},
        "by_band": by_band.reset_index().astype({"band": str}).to_dict(orient="list"),
        "primary_importance": prim_imp.to_dict(orient="list"),
        "full_importance": full_imp.to_dict(orient="list"),
    }, open("metrics/model_eval.json", "w"))
    print("\nWrote models/model_final.joblib, models/model_full.joblib, metrics/evaluation_metrics.json, "
          "metrics/error_by_band.csv, metrics/feature_importance.csv, metrics/predictions_test.csv, metrics/model_eval.json")


if __name__ == "__main__":
    main()
