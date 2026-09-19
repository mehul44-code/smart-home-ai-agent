"""Training entry points for all compact Prompt 5 models."""
from __future__ import annotations

import argparse
import json
import os
from typing import Dict

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, precision_score, r2_score, recall_score
from sklearn.model_selection import train_test_split

from backend.training.sample_data_generator import generate_training_data


FEATURES = ["indoor_temp_c", "outdoor_temp_c", "humidity_pct", "occupancy", "occupant_count",
            "ac_power_kw", "total_load_kw", "historical_average_kw", "runtime_minutes",
            "target_temp_c", "tariff_rate", "hour"]


def _split(df, target):
    return train_test_split(df[FEATURES], df[target], test_size=.2, random_state=42)


def train_all_models(output_dir: str = "backend/models", num_samples: int = 1500, seed: int = 42) -> Dict:
    os.makedirs(output_dir, exist_ok=True)
    df = generate_training_data(num_samples, seed)
    report = {"seed": seed, "samples": len(df), "models": {}}
    regressors = [("energy_model", "energy_kwh"), ("comfort_model", "comfort_score")]
    for name, target in regressors:
        xtr, xte, ytr, yte = _split(df, target)
        model = RandomForestRegressor(n_estimators=40, max_depth=8, random_state=seed, n_jobs=1).fit(xtr, ytr)
        pred = model.predict(xte)
        mae, rmse, r2 = mean_absolute_error(yte, pred), mean_squared_error(yte, pred) ** .5, r2_score(yte, pred)
        report["models"][name] = {"MAE": mae, "RMSE": rmse, "R2": r2, "mae": mae, "rmse": rmse, "r2": r2}
        joblib.dump({"model": model, "features": FEATURES, "target": target, "version": 1}, os.path.join(output_dir, name + ".joblib"), compress=3)
    for name, target in [("occupancy_model", "occupancy"), ("cooling_model", "cooling_level")]:
        xtr, xte, ytr, yte = _split(df, target)
        model = RandomForestClassifier(n_estimators=40, max_depth=8, random_state=seed, n_jobs=1).fit(xtr, ytr)
        pred = model.predict(xte)
        accuracy, precision = accuracy_score(yte, pred), precision_score(yte, pred, average="weighted", zero_division=0)
        recall, f1 = recall_score(yte, pred, average="weighted", zero_division=0), f1_score(yte, pred, average="weighted", zero_division=0)
        report["models"][name] = {"accuracy": accuracy, "precision": precision, "recall": recall, "F1": f1, "f1": f1}
        joblib.dump({"model": model, "features": FEATURES, "target": target, "version": 1}, os.path.join(output_dir, name + ".joblib"), compress=3)
    anomaly_features = ["power_kw", "historical_average_kw", "runtime_minutes", "total_load_kw", "hour"]
    anomaly = IsolationForest(n_estimators=50, contamination=.08, random_state=seed, n_jobs=1).fit(df[anomaly_features])
    joblib.dump({"model": anomaly, "features": anomaly_features, "version": 1}, os.path.join(output_dir, "anomaly_model.joblib"), compress=3)
    report["models"]["anomaly_model"] = {"algorithm": "IsolationForest", "features": anomaly_features}
    with open(os.path.join(output_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report


def train_thermal_model():
    """Compatibility wrapper: train the complete model set."""
    return train_all_models()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train smart-home ML models")
    parser.add_argument("--output-dir", default="backend/models")
    parser.add_argument("--samples", type=int, default=1500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(train_all_models(args.output_dir, args.samples, args.seed), indent=2))
