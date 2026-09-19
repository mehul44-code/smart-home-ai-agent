"""Validated, simulator-authoritative perception."""
from typing import Any, Dict

from backend.app.simulator.simulation_engine import HomeState


class PerceptionEngine:
    """Convert the simulator HomeState into a stable agent contract."""

    def observe(self, raw_state: HomeState | Dict[str, Any]) -> Dict[str, Any]:
        state = raw_state.model_dump(mode="json") if isinstance(raw_state, HomeState) else dict(raw_state)
        missing = [key for key in ("rooms", "weather", "appliances", "tariff") if key not in state]
        if missing:
            raise ValueError(f"State is missing required fields: {', '.join(missing)}")
        rooms = state["rooms"]
        if not rooms:
            raise ValueError("State must contain at least one room")
        occupancy = state.get("occupancy_detail", state.get("occupancy", {}))
        if isinstance(occupancy, bool):
            occupancy = {"is_occupied": occupancy, "total_occupants": int(occupancy)}
        for room_id, room in rooms.items():
            if room.get("temperature_c") is None or room.get("humidity_pct") is None:
                raise ValueError(f"Missing sensor values for room {room_id}")
            if not -50 <= float(room["temperature_c"]) <= 60:
                raise ValueError(f"Impossible temperature for room {room_id}")
            if not 0 <= float(room["humidity_pct"]) <= 100:
                raise ValueError(f"Invalid humidity for room {room_id}")
            if int(room.get("occupancy_count", 0)) < 0:
                raise ValueError(f"Invalid occupancy for room {room_id}")
        if occupancy.get("is_occupied") is None or int(occupancy.get("total_occupants", 0)) < 0:
            raise ValueError("Invalid occupancy state")
        tariff = state["tariff"]
        tariff_rate = float(tariff.get("rate"))
        if tariff_rate < 0 or not tariff.get("tier"):
            raise ValueError("Invalid tariff")
        for appliance_id, appliance in state["appliances"].items():
            if appliance.get("status") not in {"ON", "OFF", "ECO", "IDLE"}:
                raise ValueError(f"Invalid appliance state for {appliance_id}")
            if float(appliance.get("power_watts", 0)) < 0:
                raise ValueError(f"Negative power for appliance {appliance_id}")
        living = rooms.get("living_room") or next(iter(rooms.values()))
        target = float(living.get("target_temperature_c", 22.0))
        return {
            "timestamp": state.get("timestamp"),
            "simulated_time": state.get("simulated_time"),
            "rooms": rooms,
            "weather": state["weather"],
            "appliances": state["appliances"],
            "occupancy_detail": occupancy,
            "indoor_temp_c": float(living["temperature_c"]),
            "outdoor_temp_c": float(state["weather"]["outdoor_temperature_c"]),
            "humidity_pct": float(living["humidity_pct"]),
            "occupancy": bool(occupancy["is_occupied"]),
            "occupant_count": int(occupancy.get("total_occupants", 0)),
            "target_temp_c": target,
            "current_tariff_rate": tariff_rate,
            "tariff_tier": tariff["tier"],
            "tariff": tariff,
            "next_off_peak_minutes": int(tariff.get("next_off_peak_minutes", tariff.get("minutes_until_next_tier", 0))),
            "next_off_peak_rate": float(tariff.get("next_off_peak_rate", tariff.get("next_rate", tariff_rate))),
            "total_power_kw": float(state.get("total_load_watts", 0)) / 1000,
            "total_load_watts": float(state.get("total_load_watts", 0)),
            "total_energy_kwh": float(state.get("total_energy_kwh", 0)),
            "solar_generation_kw": float(state["weather"].get("solar_irradiance_w_m2", 0)) / 1000,
            "preferences": state.get("preferences", {}),
            "overrides": state.get("active_overrides", {}),
            "active_scenario": state.get("active_scenario"),
            "appliances_summary": {
                key: {
                    "status": value["status"],
                    "power_kw": float(value.get("power_watts", 0)) / 1000,
                    "priority": value.get("priority"),
                }
                for key, value in state["appliances"].items()
            },
        }
