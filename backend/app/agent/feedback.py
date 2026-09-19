class FeedbackEngine:
    def evaluate(self, previous_prediction: dict, observed_state: dict, decision: dict,
                 previous_state: dict | None = None) -> dict:
        actual = float(observed_state["indoor_temp_c"])
        target = float(observed_state.get("target_temp_c", 22.0))
        before = previous_state or {}
        before_energy = float(before.get("total_energy_kwh", observed_state.get("total_energy_kwh", 0)))
        after_energy = float(observed_state.get("total_energy_kwh", before_energy))
        before_comfort = max(0.0, min(100.0, 100 - abs(float(before.get("indoor_temp_c", actual)) - target) * 15))
        after_comfort = max(0.0, min(100.0, 100 - abs(actual - target) * 15))
        predicted = float(previous_prediction.get("predicted_temp_if_off_c", actual))
        return {
            "actual_indoor_temp_c": actual, "target_indoor_temp_c": target,
            "prediction_error_c": round(actual - predicted, 3),
            "comfort_before": round(before_comfort, 1), "comfort_after": round(after_comfort, 1),
            "comfort_satisfaction_pct": round(after_comfort, 1),
            "energy_before_kwh": before_energy, "energy_after_kwh": after_energy,
            "energy_delta_kwh": round(after_energy - before_energy, 4),
            "selected_action": decision.get("chosen_strategy"),
            "action_success": bool(decision.get("action_success", True)),
            "step_energy_cost_usd": round(float(observed_state.get("total_power_kw", 0)) *
                                          float(observed_state.get("tariff", {}).get("rate", 0)) / 12, 4),
            "feedback_signal": "POSITIVE" if after_comfort >= 85 else "SUBOPTIMAL",
        }
