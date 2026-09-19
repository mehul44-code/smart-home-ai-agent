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
