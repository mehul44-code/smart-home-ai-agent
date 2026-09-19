"""Candidate generation, safety filtering, and configurable utility scoring."""
from datetime import datetime, timedelta
from typing import Any, Dict, List


class ReasoningEngine:
    def __init__(self, alpha: float = 0.50, beta: float = 0.25, gamma: float = 0.15,
                 delta: float = 0.10, peak_limit_kw: float = 7.0):
        self.alpha, self.beta, self.gamma, self.delta = alpha, beta, gamma, delta
        self.peak_limit_kw = peak_limit_kw

    @staticmethod
    def _water_heater_has_demand(percept: Dict[str, Any]) -> bool:
        app = (percept.get("appliances") or {}).get("water_heater") or {}
        if not app:
            return False
        status = str(app.get("status", "OFF")).upper()
        if bool(app.get("is_user_override")):
            return True
        current_power_kw = float(app.get("power_watts", 0) or 0) / 1000.0
        if current_power_kw > 0.0 or status in {"ON", "ECO"}:
            return True
        mode = str(app.get("current_mode", "STANDARD")).upper()
        if mode in {"HEAT", "BOOST", "HOT_WATER"}:
            return True
        return False

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

    def evaluate_appliance_candidates(self, percept: Dict[str, Any], appliance_id: str) -> List[Dict[str, Any]]:
        """Score the autonomous, shiftable-load candidates without changing AC scoring."""
        app = percept["appliances"].get(appliance_id)
        if app is None:
            raise ValueError(f"Required appliance {appliance_id} is missing")
        if appliance_id == "washing_machine":
            actions = ("RUN_NOW", "DELAY", "SCHEDULE_FOR_OFF_PEAK")
        elif appliance_id == "water_heater":
            if not self._water_heater_has_demand(percept):
                current_rate = float(percept["current_tariff_rate"])
                current_load_kw = float(percept["total_power_kw"])
                return [{
                    "id": "NO_OP",
                    "label": "No water-heating demand is active; appliance remains idle.",
                    "appliance_id": appliance_id,
                    "safe": True,
                    "rejection_reason": None,
                    "total_loss": 0.0,
                    "total_utility": 0.0,
                    "rate": current_rate,
                    "current_rate": current_rate,
                    "target_rate": current_rate,
                    "delay_minutes": 0,
                    "future_rate": float(percept.get("next_off_peak_rate", current_rate)),
                    "cost_now": 0.0,
                    "cost_delayed": 0.0,
                    "current_cost": 0.0,
                    "delayed_cost": 0.0,
                    "savings": 0.0,
                    "planned_start": None,
                    "power_kw": 0.0,
                    "current_power_kw": 0.0,
                    "candidate_run_power_kw": 0.0,
                    "appliance_load_kw": 0.0,
                    "household_load_kw": round(max(0.0, current_load_kw), 3),
                    "load_before_kw": round(current_load_kw, 3),
                    "load_after_kw": round(current_load_kw, 3),
                    "peak_reduction_kw": 0.0,
                    "cost_difference": 0.0,
                    "priority": str(app.get("priority", "MEDIUM")),
                    "override_active": False,
                    "override_respected": True,
                    "is_peak": str(percept.get("tariff_tier")) in {"PEAK", "CRITICAL_PEAK"},
                    "projected_load_kw": round(current_load_kw, 3),
                    "shiftable": True,
                    "demand_detected": False,
                    "heater_addition_kw": 0.0,
                    "peak_load_before_kw": round(current_load_kw, 3),
                    "peak_load_after_kw": round(current_load_kw, 3),
                    "peak_status": "WITHIN_LIMIT",
                    "ac_interaction": "no_active_AC",
                    "washing_machine_interaction": "no_active_washer",
                }]
            actions = ("RUN_NOW", "DELAY")
        else:
            raise ValueError(f"Unsupported autonomous appliance {appliance_id}")

        preferences = percept.get("preferences") or {}
        energy_priority = float(preferences.get("energy_priority", 0.5))
        mode = preferences.get("selected_mode", "BALANCED")
        if mode == "ENERGY_SAVING":
            energy_priority = max(energy_priority, 0.8)
        priority_weight = {"CRITICAL": 2.0, "HIGH": 1.5, "MEDIUM": 1.0, "LOW": 0.65}.get(
            str(app.get("priority", "MEDIUM")), 1.0)
        current_rate = float(percept["current_tariff_rate"])
        future_rate = float(percept.get("next_off_peak_rate", percept.get("tariff", {}).get("next_rate", current_rate)))
        delay_minutes = int(percept.get("next_off_peak_minutes", percept.get("tariff", {}).get("minutes_until_next_tier", 0)))
        candidate_run_power_kw = float(app.get("nominal_power_watts", app.get("power_watts", 0))) / 1000.0
        current_power_kw = float(app.get("power_watts", 0)) / 1000.0
        shiftable = bool(app.get("is_shiftable", True))
        total_load = float(percept["total_power_kw"])
        household_load = max(0.0, total_load - current_power_kw)
        peak_limit = self.peak_limit_kw
        override = bool(app.get("is_user_override") or percept.get("overrides", {}).get(appliance_id))
        ac_kw = float(percept["appliances"].get("ac_living_room", {}).get("power_watts", 0)) / 1000.0
        washer_kw = float(percept["appliances"].get("washing_machine", {}).get("power_watts", 0)) / 1000.0
        candidates = []
        for action in actions:
            delayed = action != "RUN_NOW"
            rate = future_rate if delayed else current_rate
            if appliance_id == "water_heater":
                run_power_kw = candidate_run_power_kw if action == "RUN_NOW" else 0.0
                modeled_load = household_load + run_power_kw
            else:
                modeled_load = household_load + (candidate_run_power_kw if not delayed else 0.0)
            cost_now = candidate_run_power_kw * current_rate * 0.5
            cost_delayed = candidate_run_power_kw * rate * 0.5
            cost_saving = max(0.0, cost_now - cost_delayed)
            peak_before = max(0.0, household_load + current_power_kw - peak_limit)
            peak_after = max(0.0, modeled_load - peak_limit)
            peak_reduction = max(0.0, peak_before - peak_after)
            safety = (not override and (not delayed or shiftable))
            rejection_reason = None
            if override:
                rejection_reason = "User override active; autonomous action suppressed."
            elif delayed and not shiftable:
                rejection_reason = "Appliance cannot be shifted; delay candidate rejected."
            shift_penalty = (0.05 * priority_weight if delayed else 0.0)
            delay_penalty = (delay_minutes / 1440.0) * (1.0 - min(1.0, priority_weight / 2.0)) if delayed else 0.0
            rate_gap = max(0.0, current_rate - future_rate)
            delay_value = max(0.0, rate_gap * candidate_run_power_kw * 0.35) if delayed else 0.0
            if delayed and rate_gap <= 0.0:
                delay_penalty += 0.75
            if delayed and current_rate <= future_rate:
                delay_penalty += 0.30
            if appliance_id == "water_heater" and delayed:
                if modeled_load <= peak_limit and not (ac_kw > 0 or washer_kw > 0):
                    delay_penalty += 1.25 + (delay_minutes / 180.0)
                elif modeled_load > peak_limit or ac_kw > 0 or washer_kw > 0:
                    delay_penalty -= 0.45
            economic_term = cost_delayed if delayed else cost_now
            peak_term = peak_after * 0.55 if delayed else peak_after * 0.35
            if delayed:
                loss = economic_term * 0.65 + peak_term + shift_penalty + delay_penalty - delay_value
            else:
                loss = economic_term * 0.65 + peak_term + max(0.0, (rate_gap * candidate_run_power_kw * 0.1))
            if not safety:
                loss += 1000.0
            candidates.append({
                "id": action,
                "label": {"RUN_NOW": "Run now", "DELAY": "Delay", "SCHEDULE_FOR_OFF_PEAK": "Schedule for off-peak"}[action],
                "appliance_id": appliance_id, "safe": safety, "rejection_reason": rejection_reason,
                "total_loss": round(loss, 4),
                "total_utility": round(-loss, 4), "rate": rate, "current_rate": current_rate,
                "target_rate": rate, "delay_minutes": delay_minutes if delayed else 0,
                "future_rate": future_rate, "cost_now": round(cost_now, 4),
                "cost_delayed": round(cost_delayed, 4),
                "current_cost": round(cost_now, 4), "delayed_cost": round(cost_delayed, 4),
                "savings": round(cost_saving if delayed else 0.0, 4),
                "planned_start": ((datetime.fromisoformat(str(percept.get("simulated_time") or percept["timestamp"]).replace("Z", "+00:00"))
                                  + timedelta(minutes=delay_minutes)).isoformat()
                                 if delayed and (percept.get("simulated_time") or percept.get("timestamp")) else None),
                "power_kw": candidate_run_power_kw,
                "current_power_kw": round(current_power_kw, 3),
                "candidate_run_power_kw": round(candidate_run_power_kw, 3),
                "appliance_load_kw": round(candidate_run_power_kw, 3),
                "household_load_kw": round(household_load, 3),
                "load_before_kw": round(total_load, 3),
                "load_after_kw": round(modeled_load, 3), "peak_reduction_kw": round(peak_reduction, 3),
                "cost_difference": round(cost_saving if delayed else 0.0, 4),
                "priority": str(app.get("priority", "MEDIUM")),
                "override_active": override, "override_respected": not override or safety,
                "is_peak": str(percept.get("tariff_tier")) in {"PEAK", "CRITICAL_PEAK"},
                "projected_load_kw": round(modeled_load, 3),
                "shiftable": shiftable,
            })
            if appliance_id == "water_heater":
                candidates[-1].update({
                    "heater_addition_kw": round(run_power_kw, 3),
                    "peak_load_before_kw": round(household_load + current_power_kw, 3),
                    "peak_load_after_kw": round(modeled_load, 3),
                    "peak_status": "PEAK" if modeled_load > peak_limit else "WITHIN_LIMIT",
                    "ac_load_kw": round(ac_kw, 3),
                    "washing_machine_load_kw": round(washer_kw, 3),
                    "ac_interaction": "adds_to_active_AC_load" if ac_kw else "no_active_AC",
                    "washing_machine_interaction": "avoids_overlap_with_washer" if washer_kw else "no_active_washer",
                    "demand_detected": True,
                })
        return candidates
