from typing import Any, Dict, List


class DecisionEngine:
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
            chosen = min(candidates, key=lambda candidate: candidate["total_loss"])
        losses = sorted(c["total_loss"] for c in candidates)
        margin = losses[1] - losses[0] if len(losses) > 1 else 0.0
        return {
            "chosen_strategy": chosen["id"], "strategy_label": chosen["label"],
            "expected_loss": chosen["total_loss"], "projected_hourly_cost_usd": chosen["hourly_cost_usd"],
            "override_respected": override, "decision_margin": round(margin, 3),
            "decision_margin_type": "deterministic_loss_gap",
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
            chosen = min(candidates, key=lambda c: c["total_loss"])
        run_now = chosen["id"] == "RUN_NOW"
        return {
            "appliance_id": appliance_id, "chosen_strategy": chosen["id"],
            "selected_action": chosen["id"], "reason": chosen.get("reason") or (
                f"{chosen['label']} at {chosen['target_rate']}/kWh; "
                f"load {chosen['load_before_kw']:.2f}→{chosen['load_after_kw']:.2f} kW."
            ),
            "schedule": None if run_now else {
                "status": "SCHEDULED" if chosen["id"] == "SCHEDULE_FOR_OFF_PEAK" else "DELAYED",
                "delay_minutes": chosen["delay_minutes"], "target_rate": chosen["target_rate"],
                "target_tariff": "OFF_PEAK" if chosen["id"] == "SCHEDULE_FOR_OFF_PEAK" else "FUTURE_PERIOD",
                "scheduled_for": (percept.get("simulated_time") or percept.get("timestamp")),
            },
            "override_respected": override, "action_requested": run_now,
            "expected_cost_saving": chosen["cost_difference"], "load_before_kw": chosen["load_before_kw"],
            "load_after_kw": chosen["load_after_kw"], "success": True,
            "actions": ({appliance_id: {"action": "ON", "status": "ON", "power_kw": chosen["power_kw"]}}
                        if run_now and not override else {}),
        }
