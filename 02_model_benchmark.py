"""
02_model_benchmark.py — Mortgage max-loan project, Stage 3 (method selection).

Benchmarks 3 model families x 2 target scales (6 combos) under ONE protocol,
so the choice of model and target scale is made empirically and is auditable.

Protocol
  - Features (locked with user): applicant attributes + down payment.
    EXCLUDED: Interest Rate (risk-based price, ~determined by credit score) and
    Max Loan Amount (the held-out ground truth).
  - Split: 80/20 train/test, fixed seed. All test metrics computed on the
    ORIGINAL USD scale (log-target predictions are back-transformed first), so
    every row of the comparison table is directly comparable.
  - Also reports 5-fold CV R2 on the training set for stability.

Outputs: model_benchmark.csv (the comparison table) and prints it.
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.compose import TransformedTargetRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

CLEAN = "mortgage_clean.csv"
TARGET = "Max Loan Amount (USD)"
DROP = [TARGET, "Interest Rate"]            # leakage / off-limits
SEED = 42

CATEGORICAL = ["Gender", "Married", "Education", "Job", "Area"]
NUMERIC = ["Age", "Employment Years", "Annual Income (USD)", "Down Payment (USD)",
           "Credit Score", "Existing Monthly Debt (USD)", "Loans Repaid"]


def make_preprocessor(scale_numeric):
    num = StandardScaler() if scale_numeric else "passthrough"
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
        ("num", num, NUMERIC),
    ])


def base_models():
    # (name, estimator, scale_numeric?) — scaling only matters for the linear model.
    return [
        ("Ridge (linear)", Ridge(alpha=1.0, random_state=SEED), True),
        ("Random Forest",
         RandomForestRegressor(n_estimators=300, n_jobs=-1, random_state=SEED), False),
        ("HistGradientBoosting",
         HistGradientBoostingRegressor(max_iter=400, learning_rate=0.06,
                                       max_depth=None, random_state=SEED), False),
    ]


def metrics(y_true, y_pred):
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    return {
        "R2": r2_score(y_true, y_pred),
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": rmse,
        "MAPE_%": mape,
    }


def main():
    df = pd.read_csv(CLEAN)
    X = df.drop(columns=DROP)
    y = df[TARGET].values

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.20, random_state=SEED)

    rows = []
    for scale_name, use_log in [("raw", False), ("log", True)]:
        for mname, est, scale_num in base_models():
            pipe = Pipeline([("pre", make_preprocessor(scale_num)), ("m", est)])
            # Log target: wrap so fitting is on log1p(y) and prediction back-transforms.
            model = TransformedTargetRegressor(
                regressor=pipe, func=np.log1p, inverse_func=np.expm1) if use_log else pipe

            cv_r2 = cross_val_score(model, X_tr, y_tr, cv=5, scoring="r2", n_jobs=-1)
            model.fit(X_tr, y_tr)
            pred = model.predict(X_te)
            m = metrics(y_te, pred)
            rows.append({
                "model": mname, "target": scale_name,
                "test_R2": round(m["R2"], 4),
                "test_MAE": round(m["MAE"], 0),
                "test_RMSE": round(m["RMSE"], 0),
                "test_MAPE_%": round(m["MAPE_%"], 2),
                "cv_R2_mean": round(cv_r2.mean(), 4),
                "cv_R2_std": round(cv_r2.std(), 4),
            })
            print(f"done: {mname:22s} target={scale_name:3s}  "
                  f"test R2={m['R2']:.4f}  MAE=${m['MAE']:,.0f}  MAPE={m['MAPE_%']:.2f}%")

    table = pd.DataFrame(rows).sort_values("test_R2", ascending=False).reset_index(drop=True)
    table.to_csv("model_benchmark.csv", index=False)

    pd.set_option("display.width", 200)
    print("\n=== MODEL x TARGET-SCALE COMPARISON (test set, USD scale) ===")
    print(table.to_string(index=False))

    best = table.iloc[0]
    print(f"\nBest by test R2: {best['model']} on {best['target']} target "
          f"(R2={best['test_R2']}, MAE=${best['test_MAE']:,.0f}, MAPE={best['test_MAPE_%']}%)")


if __name__ == "__main__":
    main()
