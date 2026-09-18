from typing import Dict, Any
from backend.app.simulator.home_simulator import simulator_instance


class ActionDispatcher:
    """
    Stage 5: ACTION
    Applies the decided actions to physical or simulated smart home appliances.
    """

    def dispatch(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        dispatched = {}
        for app_id, cmd in decision.get("actions", {}).items():
            status = cmd.get("status")
            power_kw = cmd.get("power_kw", 0.0)
            setpoint_c = cmd.get("setpoint_c")

            simulator_instance.set_appliance_state(
                appliance_id=app_id,
                status=status,
                power_kw=power_kw,
                setpoint_c=setpoint_c
            )
            dispatched[app_id] = {
                "status": status,
                "power_kw": power_kw,
                "setpoint_c": setpoint_c,
                "applied": True
            }

        return {
            "dispatched_at": simulator_instance.simulation_time.isoformat(),
            "appliances_affected": list(dispatched.keys()),
            "details": dispatched
        }
