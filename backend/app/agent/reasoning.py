"""Candidate generation, safety filtering, and configurable utility scoring."""
from typing import Any, Dict, List


class ReasoningEngine:
    def __init__(self, alpha: float = 0.50, beta: float = 0.25, gamma: float = 0.15,
                 delta: float = 0.10, peak_limit_kw: float = 7.0):
        self.alpha, self.beta, self.gamma, self.delta = alpha, beta, gamma, delta
        self.peak_limit_kw = peak_limit_kw

    def evaluate_candidates(self, percept: Dict[str, Any], prediction: Dict[str, Any]) -> List[Dict[str, Any]]:
        ac = percept["appliances"].get("ac_living_room")
        if ac is None:
            raise ValueError("Required appliance ac_living_room is missing")
        current_status = ac["status"]
        base_load = max(0.0, percept["total_power_kw"] - float(ac.get("power_watts", 0)) / 1000)
        setpoints = (None, 24.0, 25.0, 26.0)
        candidates: List[Dict[str, Any]] = []
        prefs = percept.get("preferences") or {}
        mode = prefs.get("selected_mode", "BALANCED")
        mode_multiplier = {"COMFORT": (1.35, 0.75), "ENERGY_SAVING": (0.7, 1.35),
                           "BALANCED": (1.0, 1.0)}.get(mode, (1.0, 1.0))
        comfort_weight = self.alpha * mode_multiplier[0] * (1 + float(prefs.get("comfort_priority", 0)))
        energy_weight = self.beta * mode_multiplier[1] * (1 + float(prefs.get("energy_priority", 0)))
        preferred = float(prefs.get("preferred_temperature", percept["target_temp_c"]))
        for setpoint in setpoints:
            status = "OFF" if setpoint is None else "ON"
            power_kw = 0.0 if setpoint is None else float(ac["nominal_power_watts"]) / 1000
            expected = prediction["predicted_temp_if_off_c"] if setpoint is None else min(percept["indoor_temp_c"], setpoint)
            safe = (
                power_kw <= float(ac["nominal_power_watts"]) / 1000
                and (setpoint is None or 10 <= setpoint <= 35)
                and not (ac.get("is_user_override") and status != current_status)
            )
            if not safe:
                continue
            grid = max(0.0, base_load + power_kw - percept["solar_generation_kw"])
            comfort_penalty = abs(expected - percept["target_temp_c"]) * (2 if percept["occupancy"] else 0.35)
            energy_penalty = power_kw * 0.25
            cost = grid * percept["current_tariff_rate"] * 0.25
            peak = max(0.0, grid - self.peak_limit_kw) ** 2
            switching = self.delta if status != current_status else 0.0
            preference = abs((setpoint or percept["target_temp_c"]) - preferred) * 0.1
            priority = 0.0 if percept["occupancy"] else (0.5 if status == "ON" else 0.0)
            total = (comfort_weight * comfort_penalty + energy_weight * cost +
                     self.gamma * peak + switching + preference + priority)
            candidates.append({
                "id": "AC_OFF" if setpoint is None else f"AC_ON_{int(setpoint)}",
                "label": "Turn AC off" if setpoint is None else f"Set AC to {int(setpoint)}°C",
                "status": status, "setpoint_c": setpoint, "power_kw": power_kw,
                "expected_temp": round(expected, 2), "safe": True,
                "comfort_benefit": round(max(0, 100 - comfort_penalty * 10), 3),
                "predicted_temperature_effect_c": round(expected - percept["indoor_temp_c"], 3),
                "expected_energy_kwh": round(power_kw * 0.25, 3),
                "energy_penalty": round(energy_penalty, 3),
                "comfort_penalty": round(comfort_penalty, 3),
                "cost_penalty": round(cost, 3),
                "hourly_cost_usd": round(grid * percept["current_tariff_rate"], 3),
                "peak_load_impact_kw": round(grid, 3),
                "peak_penalty": round(peak, 3),
                "switching_penalty": round(switching, 3),
                "preference_penalty": round(preference, 3),
                "priority_penalty": round(priority, 3),
                "total_utility": round(-total, 3),
                "total_loss": round(total, 3),
            })
        if not candidates:
            raise ValueError("No safe candidate actions available")
        return candidates
