"""Safe model loading and small inference facade used by the agent."""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import joblib
import numpy as np

from backend.app.config import settings


class MLModelManager:
    MODEL_FILES = ("energy", "occupancy", "cooling", "comfort", "anomaly")

    def __init__(self, models_dir: Optional[str] = None):
        self.models_dir = models_dir or settings.MODELS_DIR
        self.models: Dict[str, Any] = {}
        self.load_errors: Dict[str, str] = {}
        # Kept for callers of the Prompt 3 loader contract.
        self.thermal_model = None
        self.load_model = None
        self._load_models()

    def _load_models(self):
        for name in self.MODEL_FILES:
            path = os.path.join(self.models_dir, f"{name}_model.joblib")
            if not os.path.isfile(path):
                continue
            try:
                artifact = joblib.load(path)
                if not isinstance(artifact, dict) or "model" not in artifact or not hasattr(artifact["model"], "predict"):
                    raise ValueError("invalid artifact schema")
                if int(artifact.get("version", 0)) != 1:
                    raise ValueError("unsupported model version")
                self.models[name] = artifact
            except Exception as exc:
                self.load_errors[name] = str(exc)

    def available(self, name: str) -> bool:
        return name in self.models

    def _predict(self, name: str, values: Dict[str, float]):
        artifact = self.models[name]
        features = artifact["features"]
        return artifact["model"].predict([[values.get(feature, 0.0) for feature in features]])[0]

    def predict(self, name: str, values: Dict[str, float]):
        if not self.available(name):
            return None
        try:
            return self._predict(name, values)
        except Exception:
            return None

    def predict_anomaly(self, values: Dict[str, float]) -> Optional[Dict[str, Any]]:
        if not self.available("anomaly"):
            return None
        artifact = self.models["anomaly"]
        try:
            row = [[values.get(f, 0.0) for f in artifact["features"]]]
            label = int(artifact["model"].predict(row)[0])
            raw = float(artifact["model"].decision_function(row)[0])
            score = float(np.clip(.5 - raw, 0, 1))
            actual, expected = values.get("total_load_kw", 0), values.get("historical_average_kw", 0)
            severity = "HIGH" if score >= .75 else "MEDIUM" if score >= .45 else "LOW"
            return {"anomaly": label == -1, "score": round(score, 3), "expected": expected,
                    "actual": actual, "severity": severity}
        except Exception:
            return None

    def predict_temperature_delta(self, indoor_temp, outdoor_temp, ac_power_kw, occupancy, horizon_minutes=15.0):
        values = {"indoor_temp_c": indoor_temp, "outdoor_temp_c": outdoor_temp, "ac_power_kw": ac_power_kw,
                  "occupancy": int(occupancy), "horizon_minutes": horizon_minutes}
        # Legacy thermal artifacts are intentionally not loaded: their schema is
        # incompatible with the versioned Prompt 5 artifacts.
        dt_hr = horizon_minutes / 60
        return round(((outdoor_temp - indoor_temp) / 2.5 + (.24 if occupancy else .05) - ac_power_kw * 3.2) / 18 * dt_hr, 3)

    def predict_cooling_energy_needed(self, indoor_temp, target_temp, outdoor_temp):
        return round(max(0.0, indoor_temp - target_temp) * 18 / 3.2, 2)


ml_manager = MLModelManager()
