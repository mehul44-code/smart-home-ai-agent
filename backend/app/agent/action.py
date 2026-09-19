from backend.app.simulator.home_simulator import simulator_instance


class ActionDispatcher:
    def dispatch(self, decision: dict) -> dict:
        details = {}
        for app_id, command in decision.get("actions", {}).items():
            result = simulator_instance.engine.execute_appliance_action(
                app_id, command["action"], status=command.get("status"),
                power_watts=command.get("power_kw", 0) * 1000,
                setpoint_c=command.get("setpoint_c"),
            )
            details[app_id] = {**command, "applied": bool(result.get("success")), "result": result}
        return {"dispatched_at": simulator_instance.simulation_time.isoformat(),
                "appliances_affected": list(details), "details": details,
                "success": all(item["applied"] for item in details.values()) if details else True,
                "scheduled": bool(decision.get("schedule")),
                "execution_status": "EXECUTED" if details else ("SCHEDULED" if decision.get("schedule") else "NO_OP")}
