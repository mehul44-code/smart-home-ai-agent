from typing import Dict, Any, List


class ReasoningEngine:
    """
    Stage 3: REASONING
    Evaluates candidate action profiles across appliances using a multi-objective
    utility function balancing:
    - User Comfort Penalty
    - Electricity Cost Penalty
    - Peak Load Penalty
    - Appliance Priority Rules
    """

    def __init__(self):
        # Weights can be adjusted based on user preference profile
        self.w_comfort = 1.8
        self.w_cost = 1.4
        self.w_grid = 1.0
        self.peak_limit_kw = 7.0

    def evaluate_candidates(self, percept: Dict[str, Any], prediction: Dict[str, Any]) -> List[Dict[str, Any]]:
        target_temp = percept["target_temp_c"]
        occupancy = percept["occupancy"]
        tariff_rate = percept["current_tariff_rate"]
        current_temp = percept["indoor_temp_c"]
        solar_kw = percept["solar_generation_kw"]

        # Candidate AC actions
        candidates = [
            {
                "id": "AC_OFF",
                "label": "Turn AC OFF (Maximum Energy Conservation)",
                "ac_mode": "OFF",
                "ac_setpoint": None,
                "ac_power_kw": 0.0,
                "expected_temp": prediction["predicted_temp_if_off_c"]
            },
            {
                "id": "AC_ECO",
                "label": "Set AC to ECO (24.0°C - Moderate Comfort & Cost Balance)",
                "ac_mode": "ECO",
                "ac_setpoint": 24.0,
                "ac_power_kw": 1.2,
                "expected_temp": round(min(current_temp, 24.0), 2)
            },
            {
                "id": "AC_OPTIMAL",
                "label": "Set AC to OPTIMAL (22.5°C - Balanced Target)",
                "ac_mode": "ON",
                "ac_setpoint": 22.5,
                "ac_power_kw": 1.9,
                "expected_temp": 22.5
            },
            {
                "id": "AC_MAX_COMFORT",
                "label": "Set AC to FULL CHILL (21.0°C - Aggressive Cooling)",
                "ac_mode": "ON",
                "ac_setpoint": 21.0,
                "ac_power_kw": 2.5,
                "expected_temp": 21.0
            }
        ]

        scored_candidates = []
        for cand in candidates:
            # 1. Comfort Penalty
            temp_dev = abs(cand["expected_temp"] - target_temp)
            comfort_penalty = (temp_dev ** 2) * (2.0 if occupancy else 0.3) * self.w_comfort

            # 2. Cost Penalty
            grid_draw = max(0.0, cand["ac_power_kw"] - solar_kw)
            hourly_cost = grid_draw * tariff_rate
            cost_penalty = hourly_cost * 10.0 * self.w_cost

            # 3. Peak Grid Penalty
            grid_penalty = 0.0
            if (grid_draw > self.peak_limit_kw):
                grid_penalty = ((grid_draw - self.peak_limit_kw) ** 2) * self.w_grid

            # Total composite loss (lower is better)
            total_loss = comfort_penalty + cost_penalty + grid_penalty

            scored_candidates.append({
                **cand,
                "comfort_penalty": round(comfort_penalty, 3),
                "cost_penalty": round(cost_penalty, 3),
                "grid_penalty": round(grid_penalty, 3),
                "total_loss": round(total_loss, 3),
                "hourly_cost_usd": round(hourly_cost, 3)
            })

        # Sort candidate actions by lowest total loss
        scored_candidates.sort(key=lambda c: c["total_loss"])
        return scored_candidates
