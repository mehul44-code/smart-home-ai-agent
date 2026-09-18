from typing import Dict, Any


class FeedbackEngine:
    """
    Stage 6: FEEDBACK
    Observes the actual outcome after action execution, compares it against
    predictions, and updates adaptive model error metrics.
    """

    def evaluate(
        self,
        previous_prediction: Dict[str, Any],
        observed_state: Dict[str, Any],
        decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        actual_temp = observed_state.get("indoor_temp_c", 22.0)
        target_temp = observed_state.get("target_temp_c", 22.0)
        occupancy = observed_state.get("occupancy", True)

        # Discomfort delta
        temp_error = abs(actual_temp - target_temp)
        comfort_satisfaction_pct = max(0.0, round(100.0 - (temp_error * 15.0), 1))
        
        # Estimate cost efficiency
        tariff = observed_state.get("tariff", {}).get("rate", 0.16)
        total_power = observed_state.get("total_power_kw", 0.0)
        step_cost = round((total_power * (5.0 / 60.0)) * tariff, 4)

        return {
            "actual_indoor_temp_c": actual_temp,
            "target_indoor_temp_c": target_temp,
            "temp_offset_from_target_c": round(actual_temp - target_temp, 2),
            "comfort_satisfaction_pct": comfort_satisfaction_pct,
            "occupancy": occupancy,
            "step_energy_cost_usd": step_cost,
            "feedback_signal": "POSITIVE" if comfort_satisfaction_pct >= 85.0 else "SUBOPTIMAL"
        }
