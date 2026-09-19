"""Deterministic baseline predictions with an injectable future ML contract."""
from typing import Any, Callable, Dict

from backend.app.ml.model_loader import MLModelManager


class PredictionEngine:
    def __init__(self, predictor: Callable[[Dict[str, Any]], Dict[str, Any]] | None = None,
                 model_manager: MLModelManager | None = None):
        self.predictor = predictor
        self.model_manager = model_manager or MLModelManager()

    def predict(self, percept: Dict[str, Any]) -> Dict[str, Any]:
        if self.predictor is not None:
            return {**self.predictor(percept), "model": "injected_predictor", "prediction_source": "ML"}
        indoor, outdoor = percept["indoor_temp_c"], percept["outdoor_temp_c"]
        target = percept["target_temp_c"]
        drift = round((outdoor - indoor) * 0.04 + (0.12 if percept["occupancy"] else 0), 3)
        cooling = round(max(0.0, indoor - target) * 0.18, 3)
        comfort = max(0.0, min(100.0, 100 - abs(indoor - target) * 15))
        anomaly = 0.0
        for appliance in percept["appliances"].values():
            nominal = float(appliance.get("nominal_power_watts", 0))
            if nominal:
                anomaly = max(anomaly, min(1.0, max(0.0, float(appliance.get("power_watts", 0)) / nominal - 1)))
        values = {
            "indoor_temp_c": indoor, "outdoor_temp_c": outdoor,
            "humidity_pct": percept["humidity_pct"], "occupancy": int(percept["occupancy"]),
            "occupant_count": percept["occupant_count"], "ac_power_kw": float(percept["appliances"].get("ac_living_room", {}).get("power_watts", 0)) / 1000,
            "total_load_kw": percept["total_power_kw"], "historical_average_kw": max(.1, percept["total_power_kw"]),
            "power_kw": percept["total_power_kw"],
            "runtime_minutes": 0.0, "target_temp_c": target, "tariff_rate": percept["current_tariff_rate"],
            "hour": float((percept.get("simulated_time") or "12:00")[-8:-6] or 12),
        }
        ml_used = False
        energy = self.model_manager.predict("energy", values)
        comfort_ml = self.model_manager.predict("comfort", values)
        occupancy_ml = self.model_manager.predict("occupancy", values)
        cooling_ml = self.model_manager.predict("cooling", values)
        anomaly_data = self.model_manager.predict_anomaly(values)
        if energy is not None or comfort_ml is not None or occupancy_ml is not None or cooling_ml is not None or anomaly_data is not None:
            ml_used = True
        result = {
            "model": "deterministic_baseline",
            "horizon_minutes": 15.0,
            "predicted_temp_if_off_c": round(indoor + drift, 2),
            "projected_temp_drift_c": drift,
            "cooling_energy_needed_kwh": cooling,
            "expected_energy_consumption_kwh": cooling,
            "projected_cost_immediate_usd": round(cooling * percept["current_tariff_rate"], 3),
            "comfort_score": round(comfort, 1),
            "occupancy": int(occupancy_ml) if occupancy_ml is not None else percept["occupant_count"],
            "anomaly_score": round(anomaly, 3),
            "comfort_risk": "HIGH" if percept["occupancy"] and indoor + drift > target + 1 else "LOW",
            "prediction_source": "ML" if ml_used else "BASELINE_FALLBACK",
        }
        if energy is not None:
            result["expected_energy_consumption_kwh"] = round(max(0.0, float(energy)), 3)
            result["cooling_energy_needed_kwh"] = result["expected_energy_consumption_kwh"]
        if comfort_ml is not None:
            result["comfort_score"] = round(max(0, min(100, float(comfort_ml))), 1)
        if cooling_ml is not None:
            result["cooling_level"] = str(cooling_ml)
        if anomaly_data is not None:
            result.update({"anomaly": anomaly_data["anomaly"], "anomaly_score": anomaly_data["score"],
                           "anomaly_expected": anomaly_data["expected"], "anomaly_actual": anomaly_data["actual"],
                           "anomaly_severity": anomaly_data["severity"]})
        return result
