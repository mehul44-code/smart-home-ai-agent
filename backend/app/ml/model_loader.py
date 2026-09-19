import os
import joblib
import numpy as np
from typing import Dict, Any, Optional
from backend.app.config import settings


class MLModelManager:
    """
    Loads, caches, and provides inference for ML models.
    Falls back gracefully to calibrated thermodynamic physics heuristics
    if trained model artifacts are not yet generated.
    """

    def __init__(self):
        self.models_dir = settings.MODELS_DIR
        self.thermal_model = None
        self.load_model = None
        self._load_models()

    def _load_models(self):
        thermal_path = os.path.join(self.models_dir, "thermal_model.joblib")
        load_path = os.path.join(self.models_dir, "load_model.joblib")

        if os.path.exists(thermal_path):
            try:
                self.thermal_model = joblib.load(thermal_path)
            except Exception as e:
                print(f"Warning: Failed to load thermal model from {thermal_path}: {e}")

        if os.path.exists(load_path):
            try:
                self.load_model = joblib.load(load_path)
            except Exception as e:
                print(f"Warning: Failed to load load model from {load_path}: {e}")

    def predict_temperature_delta(
        self,
        indoor_temp: float,
        outdoor_temp: float,
        ac_power_kw: float,
        occupancy: bool,
        horizon_minutes: float = 15.0
    ) -> float:
        """
        Predicts temperature change (ΔT) over the upcoming horizon.
        Uses trained scikit-learn regressor if present, otherwise physics equation.
        """
        if self.thermal_model is not None:
            try:
                import pandas as pd
                features = pd.DataFrame([{
                    "indoor_temp_c": indoor_temp,
                    "outdoor_temp_c": outdoor_temp,
                    "ac_power_kw": ac_power_kw,
                    "occupancy": int(occupancy),
                    "horizon_minutes": horizon_minutes
                }])
                return float(self.thermal_model.predict(features)[0])
            except Exception:
                pass

        # Calibrated physics fallback:
        # q_env = (T_out - T_in)/2.5, q_int = 0.2, q_cool = ac_power * 3.2
        dt_hr = horizon_minutes / 60.0
        q_env = (outdoor_temp - indoor_temp) / 2.5
        q_int = 0.24 if occupancy else 0.05
        q_cool = ac_power_kw * 3.2
        c_th = 18.0
        dT = ((q_env + q_int - q_cool) / c_th) * dt_hr
        return round(dT, 3)

    def predict_cooling_energy_needed(
        self,
        indoor_temp: float,
        target_temp: float,
        outdoor_temp: float
    ) -> float:
        """
        Estimates the required electric energy (kWh) to drive indoor temp to target.
        """
        temp_gap = max(0.0, indoor_temp - target_temp)
        c_th = 18.0
        cop = 3.2
        thermal_energy_needed_kwh = temp_gap * c_th
        electric_energy_kwh = thermal_energy_needed_kwh / cop
        return round(electric_energy_kwh, 2)


ml_manager = MLModelManager()
