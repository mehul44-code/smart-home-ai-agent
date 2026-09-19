from typing import Dict, Any
from backend.app.ml.model_loader import ml_manager


class PredictionEngine:
    """
    Stage 2: PREDICTION
    Applies predictive ML models and thermodynamic equations to forecast:
    - Indoor temperature drift if no action is taken
    - Required cooling energy to reach comfort target
    - Expected energy cost under current tariff tier
    """

    def predict(self, percept: Dict[str, Any]) -> Dict[str, Any]:
        indoor_temp = percept["indoor_temp_c"]
        outdoor_temp = percept["outdoor_temp_c"]
        target_temp = percept["target_temp_c"]
        occupancy = percept["occupancy"]
        tariff_rate = percept["current_tariff_rate"]

        # Predict natural thermal drift over the next 15 minutes (with AC OFF)
        temp_drift_off = ml_manager.predict_temperature_delta(
            indoor_temp=indoor_temp,
            outdoor_temp=outdoor_temp,
            ac_power_kw=0.0,
            occupancy=occupancy,
            horizon_minutes=15.0
        )
        predicted_temp_if_off = round(indoor_temp + temp_drift_off, 2)

        # Predict cooling energy required to reach target
        cooling_energy_needed_kwh = ml_manager.predict_cooling_energy_needed(
            indoor_temp=indoor_temp,
            target_temp=target_temp,
            outdoor_temp=outdoor_temp
        )

        # Predict projected cost for immediate aggressive cooling
        projected_cost_immediate = round(cooling_energy_needed_kwh * tariff_rate, 3)

        return {
            "predicted_temp_if_off_c": predicted_temp_if_off,
            "projected_temp_drift_c": temp_drift_off,
            "cooling_energy_needed_kwh": cooling_energy_needed_kwh,
            "projected_cost_immediate_usd": projected_cost_immediate,
            "comfort_risk": "HIGH" if (predicted_temp_if_off > target_temp + 2.0 and occupancy) else "LOW"
        }
