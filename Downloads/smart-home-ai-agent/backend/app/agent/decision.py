from typing import Dict, Any, List


class DecisionEngine:
    """
    Stage 4: DECISION
    Selects the best overall action from evaluated candidates,
    incorporating appliance priority rules and peak demand shifting.
    """

    def decide(self, percept: Dict[str, Any], evaluated_candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        best_ac = evaluated_candidates[0]
        tariff_tier = percept["tariff_tier"]
        
        # Decide shiftable secondary loads based on tariff and peak
        appliance_actions = {
            "ac_living_room": {
                "action": "SET_MODE",
                "status": best_ac["ac_mode"],
                "power_kw": best_ac["ac_power_kw"],
                "setpoint_c": best_ac["ac_setpoint"]
            }
        }

        # Dynamic load shifting for shiftable devices
        if tariff_tier in ("PEAK", "CRITICAL_PEAK"):
            # Defer EV charging and water heater during peak tariffs
            appliance_actions["ev_charger"] = {
                "action": "DEFER",
                "status": "OFF",
                "power_kw": 0.0,
                "reason": "Peak tariff in effect. Deferring EV charging to Off-Peak."
            }
            appliance_actions["water_heater"] = {
                "action": "ECO_MAINTAIN",
                "status": "OFF",
                "power_kw": 0.0,
                "reason": "Sufficient water thermal storage. Suspending heating elements."
            }
        else:
            # Standard or Off-Peak allows charging / heating
            appliance_actions["ev_charger"] = {
                "action": "CHARGE",
                "status": "ON",
                "power_kw": 3.3,
                "reason": "Off-peak or standard tariff enables cost-effective charging."
            }
            appliance_actions["water_heater"] = {
                "action": "HEAT",
                "status": "ON",
                "power_kw": 1.2,
                "reason": "Preheating water tank before upcoming peak tier."
            }

        return {
            "chosen_strategy": best_ac["id"],
            "strategy_label": best_ac["label"],
            "expected_loss": best_ac["total_loss"],
            "projected_hourly_cost_usd": best_ac["hourly_cost_usd"],
            "actions": appliance_actions
        }
