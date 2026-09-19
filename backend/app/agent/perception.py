from typing import Dict, Any


class PerceptionEngine:
    """
    Stage 1: PERCEPTION
    Ingests and normalizes raw telemetry, environmental sensors, occupancy,
    and electricity market tariff signals.
    """

    def observe(self, raw_state: Dict[str, Any]) -> Dict[str, Any]:
        """Processes raw telemetry into structured percepts."""
        tariff = raw_state.get("tariff", {})
        appliances = raw_state.get("appliances", {})
        
        percept = {
            "timestamp": raw_state.get("timestamp"),
            "indoor_temp_c": raw_state.get("indoor_temp_c", 24.0),
            "outdoor_temp_c": raw_state.get("outdoor_temp_c", 30.0),
            "humidity_pct": raw_state.get("humidity_pct", 50.0),
            "occupancy": raw_state.get("occupancy", False),
            "occupant_count": raw_state.get("occupant_count", 0),
            "target_temp_c": raw_state.get("target_temp_c", 22.0),
            "current_tariff_rate": tariff.get("rate", 0.16),
            "tariff_tier": tariff.get("tier", "STANDARD"),
            "solar_generation_kw": raw_state.get("solar_generation_kw", 0.0),
            "total_power_kw": raw_state.get("total_power_kw", 0.0),
            "grid_power_kw": raw_state.get("grid_power_kw", 0.0),
            "appliances_summary": {
                app_id: {
                    "status": data.get("status"),
                    "power_kw": data.get("power_kw"),
                    "priority": data.get("priority")
                }
                for app_id, data in appliances.items()
            }
        }
        return percept
