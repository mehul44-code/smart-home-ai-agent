from typing import Dict, Any, Callable
from pydantic import BaseModel, Field

from backend.app.simulator.weather import WeatherCondition
from backend.app.simulator.tariff import TariffTier


class DemoScenario(BaseModel):
    id: str
    name: str
    description: str
    purpose: str


class ScenarioRegistry:
    """
    Defines and activates predefined demonstration scenarios for competition judging.
    """

    SCENARIOS: Dict[str, DemoScenario] = {
        "SCENARIO_1_NORMAL_HOME": DemoScenario(
            id="SCENARIO_1_NORMAL_HOME",
            name="Normal Home",
            description="Baseline environment with 24°C indoor temp, 0 occupancy, AC OFF.",
            purpose="Demonstrate standard baseline equilibrium conditions."
        ),
        "SCENARIO_2_HOT_OCCUPIED_ROOM": DemoScenario(
            id="SCENARIO_2_HOT_OCCUPIED_ROOM",
            name="Hot Occupied Room",
            description="Indoor temperature climbs to 29°C with 2 occupants and 70% humidity. AC is OFF.",
            purpose="Demonstrate high comfort violation requiring autonomous cooling."
        ),
        "SCENARIO_3_EMPTY_ROOM": DemoScenario(
            id="SCENARIO_3_EMPTY_ROOM",
            name="Empty Room Cooling Waste",
            description="Temperature 29°C, 0 occupants, but AC is ON.",
            purpose="Demonstrate wasteful cooling in an unoccupied home suitable for eco-curtailment."
        ),
        "SCENARIO_4_PEAK_TARIFF": DemoScenario(
            id="SCENARIO_4_PEAK_TARIFF",
            name="Peak Tariff Load Shift",
            description="Critical Peak tariff in effect (₹12/kWh) with multiple heavy loads active.",
            purpose="Trigger agent financial cost reasoning and non-critical load deferral."
        ),
        "SCENARIO_5_HIGH_ENERGY_LOAD": DemoScenario(
            id="SCENARIO_5_HIGH_ENERGY_LOAD",
            name="High Simultaneous Energy Load",
            description="AC (1500W), Water Heater (2000W), and Washing Machine (800W) all running concurrently.",
            purpose="Exceed household peak demand threshold to test grid peak shaving."
        ),
        "SCENARIO_6_ENERGY_ANOMALY": DemoScenario(
            id="SCENARIO_6_ENERGY_ANOMALY",
            name="Appliance Energy Anomaly",
            description="Washing machine drawing 1700W (more than 2x nominal 800W load).",
            purpose="Simulate hardware malfunction or motor fault for anomaly detection."
        ),
        "SCENARIO_7_USER_OVERRIDE": DemoScenario(
            id="SCENARIO_7_USER_OVERRIDE",
            name="User Manual Override",
            description="User manually overrides AC to ON contrary to eco policy.",
            purpose="Verify that manual user overrides take precedence and are strictly preserved."
        )
    }

    @classmethod
    def apply_scenario(cls, scenario_id: str, engine: Any) -> Dict[str, Any]:
        """Applies scenario environmental and appliance configurations to the simulation engine."""
        scenario_key = scenario_id.upper().replace(" ", "_").replace("-", "_")

        # Fallback matching
        matched_id = None
        for k in cls.SCENARIOS:
            if scenario_key in k or k in scenario_key:
                matched_id = k
                break

        if not matched_id:
            return {"success": False, "error": f"Unknown scenario '{scenario_id}'. Available: {list(cls.SCENARIOS.keys())}"}

        scenario = cls.SCENARIOS[matched_id]
        engine.reset()
        engine.active_scenario = scenario.id

        if matched_id == "SCENARIO_1_NORMAL_HOME":
            engine.change_temperature("living_room", 24.0)
            engine.change_temperature("bedroom", 24.0)
            engine.change_temperature("kitchen", 24.0)
            engine.change_occupancy(0, {"living_room": 0, "bedroom": 0, "kitchen": 0})
            engine.appliances.execute_action("ac_living_room", "OFF")
            engine.change_weather(WeatherCondition.MILD, temp_c=25.0, humidity_pct=50.0)

        elif matched_id == "SCENARIO_2_HOT_OCCUPIED_ROOM":
            engine.change_temperature("living_room", 29.0)
            engine.change_temperature("bedroom", 28.5)
            engine.change_temperature("kitchen", 29.0)
            engine.environment.set_room_humidity("living_room", 70.0)
            engine.change_occupancy(2, {"living_room": 2, "bedroom": 0, "kitchen": 0})
            engine.appliances.execute_action("ac_living_room", "OFF")
            engine.change_weather(WeatherCondition.HOT, temp_c=35.0, humidity_pct=65.0)

        elif matched_id == "SCENARIO_3_EMPTY_ROOM":
            engine.change_temperature("living_room", 29.0)
            engine.change_occupancy(0, {"living_room": 0, "bedroom": 0, "kitchen": 0})
            engine.appliances.execute_action("ac_living_room", "ON", power_watts=1500.0, setpoint_c=21.0)
            engine.change_weather(WeatherCondition.HOT, temp_c=34.0, humidity_pct=55.0)

        elif matched_id == "SCENARIO_4_PEAK_TARIFF":
            engine.change_tariff(TariffTier.PEAK, rate=12.0)
            engine.change_occupancy(2, {"living_room": 2, "bedroom": 0, "kitchen": 0})
            engine.appliances.execute_action("ac_living_room", "ON", power_watts=1500.0)
            engine.appliances.execute_action("tv_living_room", "ON", power_watts=120.0)
            engine.appliances.execute_action("water_heater", "ON", power_watts=2000.0)
            engine.appliances.execute_action("lights_living_room", "ON", power_watts=15.0)

        elif matched_id == "SCENARIO_5_HIGH_ENERGY_LOAD":
            engine.appliances.execute_action("ac_living_room", "ON", power_watts=1500.0)
            engine.appliances.execute_action("water_heater", "ON", power_watts=2000.0)
            engine.appliances.execute_action("washing_machine", "ON", power_watts=800.0)

        elif matched_id == "SCENARIO_6_ENERGY_ANOMALY":
            # Abnormal spike in washing machine power (1700W instead of 800W)
            engine.appliances.execute_action("washing_machine", "ON", power_watts=1700.0)

        elif matched_id == "SCENARIO_7_USER_OVERRIDE":
            # User manually forces AC to ON
            engine.appliances.execute_action(
                "ac_living_room",
                "ON",
                power_watts=1500.0,
                setpoint_c=20.0,
                is_user_override=True,
                override_reason="User explicitly requested maximum cooling"
            )

        return {
            "success": True,
            "scenario_id": scenario.id,
            "name": scenario.name,
            "purpose": scenario.purpose,
            "state_snapshot": engine.get_current_home_state().model_dump()
        }
