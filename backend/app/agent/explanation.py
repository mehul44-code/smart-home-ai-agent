from typing import Dict, Any


class ExplanationEngine:
    """
    Stage 7: EXPLANATION
    Synthesizes clear, human-interpretable natural language explanations
    revealing *why* the agent chose a specific strategy over alternatives.
    """

    def explain(
        self,
        percept: Dict[str, Any],
        prediction: Dict[str, Any],
        decision: Dict[str, Any],
        feedback: Dict[str, Any]
    ) -> str:
        indoor = percept["indoor_temp_c"]
        outdoor = percept["outdoor_temp_c"]
        occupancy = percept["occupancy"]
        tariff_tier = percept["tariff_tier"]
        tariff_rate = percept["current_tariff_rate"]
        strategy = decision["chosen_strategy"]
        
        occ_str = "occupied" if occupancy else "unoccupied"
        
        explanation_parts = [
            f"Perception: Outdoor temp is {outdoor}°C with indoor temp at {indoor}°C in an {occ_str} home. "
            f"Current grid tariff is {tariff_tier} (${tariff_rate:.2f}/kWh).",
        ]

        if strategy == "AC_ECO":
            explanation_parts.append(
                f"Prediction & Reasoning: Without cooling, indoor temp would drift to {prediction['predicted_temp_if_off_c']}°C. "
                f"However, aggressive chilling during {tariff_tier} tariff would incur significant electrical cost. "
                "Selected ECO mode (24.0°C) to strike the optimal mathematical trade-off between occupant thermal comfort "
                f"and peak electricity avoidance."
            )
        elif strategy == "AC_OPTIMAL":
            explanation_parts.append(
                f"Prediction & Reasoning: Selected balanced 22.5°C cooling to satisfy occupant preference while solar PV generation "
                f"offsets grid demand."
            )
        elif strategy == "AC_OFF":
            explanation_parts.append(
                "Prediction & Reasoning: Home is currently unoccupied or indoor temperature is within natural comfort band. "
                "Suspended HVAC cooling to eliminate unnecessary grid consumption."
            )
        else:
            explanation_parts.append(
                f"Strategy: Executed {strategy} to satisfy priority constraints and maintain user comfort."
            )

        # Deferrals explanation
        actions = decision.get("actions", {})
        if actions.get("ev_charger", {}).get("status") == "OFF" and tariff_tier in ("PEAK", "CRITICAL_PEAK"):
            explanation_parts.append(
                "Peak Load Shifting: Deferred EV charging to prevent household demand from compounding peak grid tariffs."
            )

        explanation_parts.append(
            f"Feedback: Post-action comfort satisfaction rated at {feedback.get('comfort_satisfaction_pct', 90)}%."
        )

        return " ".join(explanation_parts)
