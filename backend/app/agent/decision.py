from typing import Any, Dict, List


class DecisionEngine:
    @staticmethod
    def _select_best_valid_candidate(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        valid_candidates = [candidate for candidate in candidates if candidate.get("safe", True)]
        if not valid_candidates:
            if not candidates:
                raise ValueError("No candidate actions available")
            return max(candidates, key=lambda candidate: float(candidate.get("total_utility", 0.0)))
        return max(valid_candidates, key=lambda candidate: float(candidate.get("total_utility", 0.0)))

    def decide(self, percept: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        ac = percept["appliances"]["ac_living_room"]
        override = bool(ac.get("is_user_override") or percept.get("overrides", {}).get("ac_living_room"))
        if override:
            chosen = next((c for c in candidates if c["status"] == ac["status"] and
                           (c["setpoint_c"] is None or c["setpoint_c"] == ac.get("setpoint_c"))), None)
            if chosen is None:
                chosen = {"id": "AC_USER_OVERRIDE", "label": "Preserve user override", "status": ac["status"],
                          "setpoint_c": ac.get("setpoint_c"), "power_kw": float(ac.get("power_watts", 0)) / 1000,
                          "hourly_cost_usd": float(ac.get("power_watts", 0)) / 1000 * percept["current_tariff_rate"],
                          "total_loss": 0.0, "total_utility": 0.0, "safe": True}
        else:
            chosen = self._select_best_valid_candidate(candidates)
        losses = sorted(float(c.get("total_loss", 0.0)) for c in candidates)
        margin = losses[1] - losses[0] if len(losses) > 1 else 0.0
        return {
            "chosen_strategy": chosen["id"], "strategy_label": chosen["label"],
            "expected_loss": chosen["total_loss"], "projected_hourly_cost_usd": chosen["hourly_cost_usd"],
            "override_respected": override, "decision_margin": round(margin, 3),
            "decision_margin_type": "deterministic_utility_gap",
            "candidate_debug": [{
                "candidate_id": c["id"],
                "label": c.get("label"),
                "safe": c.get("safe", True),
                "rejection_reason": c.get("rejection_reason"),
                "total_utility": c.get("total_utility"),
                "total_loss": c.get("total_loss"),
            } for c in candidates],
            "actions": {"ac_living_room": {"action": "OFF" if chosen["status"] == "OFF" else "ON",
                                             "status": chosen["status"], "power_kw": chosen["power_kw"],
                                             "setpoint_c": chosen["setpoint_c"]}},
        }

    def decide_appliance(self, percept: dict, candidates: List[dict], appliance_id: str) -> dict:
        app = percept["appliances"][appliance_id]
        override = bool(app.get("is_user_override") or percept.get("overrides", {}).get(appliance_id))
        if override:
            # Preserve the appliance's observed state rather than presenting a
            # new autonomous command that could be mistaken for a reversal.
            chosen_id = "RUN_NOW" if app.get("status") == "ON" else "DELAY"
            chosen = next(c for c in candidates if c["id"] == chosen_id)
            chosen = {**chosen, "safe": True, "override_respected": True,
                      "reason": "USER_OVERRIDE_ACTIVE; user state preserved with no autonomous reversal."}
        else:
            chosen = self._select_best_valid_candidate(candidates)
        run_now = chosen["id"] == "RUN_NOW"
        is_heater = appliance_id == "water_heater"
        if chosen["id"] == "NO_OP":
            reason = "No water-heating demand is active; appliance remains idle."
            schedule = None
            selected_action = "NO_OP"
            action_requested = False
            actions = {}
            expected_cost_saving = 0.0
            load_before_kw = chosen["load_before_kw"]
            load_after_kw = chosen["load_after_kw"]
            household_load_kw = chosen["household_load_kw"]
            appliance_load_kw = chosen["appliance_load_kw"]
        else:
            if is_heater:
                reason = (
                    f"Water-heater peak reasoning: household load {chosen['household_load_kw']:.2f} kW "
                    f"+ heater {chosen['heater_addition_kw']:.2f} kW = projected {chosen['projected_load_kw']:.2f} kW; "
                    f"{chosen['peak_status'].replace('_', ' ').lower()} at {chosen['target_rate']:.2f} ₹/kWh. "
                    f"AC interaction: {chosen['ac_interaction'].replace('_', ' ')}; "
                    f"washing-machine interaction: {chosen['washing_machine_interaction'].replace('_', ' ')}."
                )
            else:
                reason = (
                    f"Washing-machine tariff reasoning: current {chosen['current_rate']:.2f} ₹/kWh, "
                    f"future {chosen['future_rate']:.2f} ₹/kWh; current cost ₹{chosen['current_cost']:.2f}, "
                    f"delayed cost ₹{chosen['delayed_cost']:.2f}, saving ₹{chosen['savings']:.2f}. "
                    f"Household load {chosen['household_load_kw']:.2f} kW and washer load "
                    f"{chosen['appliance_load_kw']:.2f} kW."
                )
            schedule = None if run_now else {
                "status": "SCHEDULED" if chosen["id"] == "SCHEDULE_FOR_OFF_PEAK" else "DELAYED",
                "delay_minutes": chosen["delay_minutes"], "target_rate": chosen["target_rate"],
                "target_tariff": "OFF_PEAK" if chosen["id"] == "SCHEDULE_FOR_OFF_PEAK" else "FUTURE_PERIOD",
                "scheduled_for": chosen.get("planned_start") or (percept.get("simulated_time") or percept.get("timestamp")),
            }
            selected_action = chosen["id"]
            action_requested = run_now
            actions = ({appliance_id: {"action": "ON", "status": "ON", "power_kw": chosen["power_kw"]}}
                       if run_now and not override else {})
            expected_cost_saving = chosen["cost_difference"]
            load_before_kw = chosen["load_before_kw"]
            load_after_kw = chosen["load_after_kw"]
            household_load_kw = chosen["household_load_kw"]
            appliance_load_kw = chosen["appliance_load_kw"]
        if override:
            reason = "User override preserved. " + reason
        return {
            "appliance_id": appliance_id, "chosen_strategy": chosen["id"],
            "selected_action": selected_action, "reason": chosen.get("reason") or (
                f"{chosen['label']}. {reason}"
            ),
            "schedule": schedule,
            "override_respected": override, "action_requested": action_requested,
            "expected_cost_saving": expected_cost_saving, "load_before_kw": load_before_kw,
            "load_after_kw": load_after_kw, "success": True,
            "current_tariff_rate": chosen["current_rate"], "future_tariff_rate": chosen["future_rate"],
            "current_cost": chosen["current_cost"], "delayed_cost": chosen["delayed_cost"],
            "savings": chosen["savings"], "delay_minutes": chosen["delay_minutes"],
            "planned_start": chosen.get("planned_start"), "household_load_kw": household_load_kw,
            "appliance_load_kw": appliance_load_kw, "priority": chosen["priority"],
            "override_active": chosen["override_active"],
            "is_peak": chosen["is_peak"],
            "candidate_debug": [{
                "candidate_id": c["id"],
                "label": c.get("label"),
                "safe": c.get("safe", True),
                "rejection_reason": c.get("rejection_reason"),
                "total_utility": c.get("total_utility"),
                "total_loss": c.get("total_loss"),
                "current_rate": c.get("current_rate"),
                "future_rate": c.get("future_rate"),
                "household_load_kw": c.get("household_load_kw"),
                "appliance_load_kw": c.get("appliance_load_kw"),
                "current_cost": c.get("current_cost"),
                "delayed_cost": c.get("delayed_cost"),
                "savings": c.get("savings"),
            } for c in candidates],
            **({"heater_addition_kw": chosen["heater_addition_kw"],
                "projected_load_kw": chosen["projected_load_kw"],
                "peak_load_before_kw": chosen["peak_load_before_kw"],
                "peak_load_after_kw": chosen["peak_load_after_kw"],
                "peak_status": chosen["peak_status"],
                "ac_interaction": chosen["ac_interaction"],
                "washing_machine_interaction": chosen["washing_machine_interaction"]}
               if is_heater and chosen.get("id") != "NO_OP" else {}),
            "actions": actions,
        }
