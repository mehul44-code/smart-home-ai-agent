import datetime
from typing import Dict, Any, Optional
from backend.app.simulator.simulation_engine import SimulationEngine, HomeState
from backend.app.simulator.scenarios import ScenarioRegistry


class SmartHomeSimulatorFacade:
    """
    High-level facade wrapping the multi-room SimulationEngine.
    Provides 100% backward compatibility for existing REST endpoints, WebSocket streams,
    and agent cognitive steps, while exposing full multi-room capabilities.
    """

    def __init__(self):
        self.engine = SimulationEngine()

    @property
    def simulation_time(self) -> datetime.datetime:
        return self.engine.current_time

    @property
    def appliances(self) -> Dict[str, Dict[str, Any]]:
        """Exposes appliance dictionary in kW format for legacy modules."""
        legacy_dict = {}
        for app_id, app in self.engine.appliances.appliances.items():
            legacy_dict[app_id] = {
                "name": app.name,
                "category": app.room.upper(),
                "status": app.status,
                "power_kw": round(app.power_watts / 1000.0, 3),
                "power_watts": app.power_watts,
                "rated_power_kw": round(app.nominal_power_watts / 1000.0, 3),
                "priority": app.priority.value,
                "comfort_impact": app.comfort_impact.value,
                "setpoint_c": app.setpoint_c,
                "is_user_override": app.is_user_override,
                "total_energy_kwh": app.total_energy_kwh
            }
        return legacy_dict

    def step(self, dt_minutes: float = 5.0) -> Dict[str, Any]:
        """
        Advances the simulation engine by dt_minutes and returns
        both the backward-compatible dictionary schema and the rich multi-room state.
        """
        home_state: HomeState = self.engine.step(dt_minutes=dt_minutes)

        lr = home_state.rooms.get("living_room")
        indoor_temp = lr.temperature_c if lr else 24.0
        indoor_humidity = lr.humidity_pct if lr else 50.0

        solar_kw = round(home_state.weather.solar_irradiance_w_m2 * 0.003, 2)
        total_kw = round(home_state.total_load_watts / 1000.0, 3)
        grid_kw = max(0.0, round(total_kw - solar_kw, 3))

        tariff_dict = {
            "tier": home_state.tariff.tier.value,
            "rate": home_state.tariff.rate,
            "currency": home_state.tariff.currency,
            "unit": f"{home_state.tariff.currency}/kWh",
            "minutes_until_next_tier": home_state.tariff.minutes_until_next_tier
        }

        # Compatible legacy payload
        return {
            "timestamp": home_state.timestamp,
            "indoor_temp_c": indoor_temp,
            "outdoor_temp_c": home_state.weather.outdoor_temperature_c,
            "humidity_pct": indoor_humidity,
            "occupancy": home_state.occupancy.is_occupied,
            "occupant_count": home_state.occupancy.total_occupants,
            "target_temp_c": lr.target_temperature_c if lr else 22.0,
            "solar_generation_kw": solar_kw,
            "total_power_kw": total_kw,
            "total_power_watts": home_state.total_load_watts,
            "grid_power_kw": grid_kw,
            "tariff": tariff_dict,
            "appliances": self.appliances,
            "total_energy_kwh": home_state.total_energy_kwh,
            "estimated_cost_accumulated": home_state.estimated_cost_accumulated,
            # Full multi-room state
            "rooms": {r_id: r.model_dump() for r_id, r in home_state.rooms.items()},
            "sensors": {s_id: s.model_dump() for s_id, s in home_state.sensors.items()},
            "weather": home_state.weather.model_dump(),
            "occupancy_detail": home_state.occupancy.model_dump()
        }

    def set_appliance_state(
        self,
        appliance_id: str,
        status: str,
        power_kw: float,
        setpoint_c: Optional[float] = None
    ):
        """Allows external actuator/agent to update appliance state."""
        power_w = power_kw * 1000.0 if power_kw is not None else None
        self.engine.execute_appliance_action(
            appliance_id=appliance_id,
            action="SET_MODE" if status == "ECO" else status,
            status=status,
            power_watts=power_w,
            setpoint_c=setpoint_c
        )

    def load_scenario(self, scenario_id: str) -> Dict[str, Any]:
        """Loads a predefined demonstration scenario."""
        return ScenarioRegistry.apply_scenario(scenario_id, self.engine)

    def get_current_home_state(self) -> HomeState:
        return self.engine.get_current_home_state()


# Singleton simulator instance
simulator_instance = SmartHomeSimulatorFacade()
