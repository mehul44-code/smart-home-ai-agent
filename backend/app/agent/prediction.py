"""Deterministic baseline predictions with an injectable future ML contract."""
from typing import Any, Callable, Dict


class PredictionEngine:
    def __init__(self, predictor: Callable[[Dict[str, Any]], Dict[str, Any]] | None = None):
        self.predictor = predictor

    def predict(self, percept: Dict[str, Any]) -> Dict[str, Any]:
        if self.predictor is not None:
            return {**self.predictor(percept), "model": "injected_predictor"}
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
        return {
            "model": "deterministic_baseline",
            "horizon_minutes": 15.0,
            "predicted_temp_if_off_c": round(indoor + drift, 2),
            "projected_temp_drift_c": drift,
            "cooling_energy_needed_kwh": cooling,
            "expected_energy_consumption_kwh": cooling,
            "projected_cost_immediate_usd": round(cooling * percept["current_tariff_rate"], 3),
            "comfort_score": round(comfort, 1),
            "occupancy": percept["occupant_count"],
            "anomaly_score": round(anomaly, 3),
            "comfort_risk": "HIGH" if percept["occupancy"] and indoor + drift > target + 1 else "LOW",
        }
