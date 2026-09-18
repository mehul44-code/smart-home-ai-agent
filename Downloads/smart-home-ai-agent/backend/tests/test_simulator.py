import datetime
import pytest
from backend.app.simulator.simulation_engine import SimulationEngine
from backend.app.simulator.scenarios import ScenarioRegistry
from backend.app.simulator.tariff import TariffTier
from backend.app.simulator.weather import WeatherCondition


@pytest.fixture
def sim():
    """Deterministic simulation engine fixture."""
    return SimulationEngine(
        start_time=datetime.datetime(2026, 6, 15, 14, 0, 0),
        default_step_minutes=1.0,
        currency="₹"
    )


def test_1_home_initializes_correctly(sim):
    """Test 1: Home initializes correctly with 3 rooms and default appliances."""
    state = sim.get_current_home_state()
    assert state.is_running is True
    assert len(state.rooms) == 3
    assert set(state.rooms.keys()) == {"living_room", "bedroom", "kitchen"}
    
    # Verify key appliances exist
    app_ids = set(state.appliances.keys())
    assert "ac_living_room" in app_ids
    assert "fan_bedroom" in app_ids
    assert "refrigerator" in app_ids
    assert "water_heater" in app_ids
    assert "washing_machine" in app_ids
    assert "tv_living_room" in app_ids


def test_2_sensor_values_within_valid_ranges(sim):
    """Test 2: Sensor values stay within physically realistic bounds."""
    state = sim.step(dt_minutes=5.0)
    sensors = state.sensors

    for room_id in ("living_room", "bedroom", "kitchen"):
        temp_s = sensors[f"sensor_temp_{room_id}"]
        assert 15.0 <= temp_s.value <= 45.0, f"Temp sensor out of bounds: {temp_s.value}"
        assert temp_s.unit == "°C"

        hum_s = sensors[f"sensor_humidity_{room_id}"]
        assert 10.0 <= hum_s.value <= 100.0, f"Humidity sensor out of bounds: {hum_s.value}"
        assert hum_s.unit == "%"

        lux_s = sensors[f"sensor_light_{room_id}"]
        assert 0.0 <= lux_s.value <= 2000.0, f"Light sensor out of bounds: {lux_s.value}"
        assert lux_s.unit == "Lux"


def test_3_temperature_changes_logically_with_time(sim):
    """Test 3: Outdoor temperature follows diurnal curve and affects indoor temps."""
    # Start at 06:00 (cool morning)
    sim.current_time = datetime.datetime(2026, 6, 15, 6, 0, 0)
    morning_state = sim.step(dt_minutes=1.0)
    morning_outdoor = morning_state.weather.outdoor_temperature_c

    # Advance to 15:00 (mid-afternoon heat peak)
    sim.current_time = datetime.datetime(2026, 6, 15, 15, 0, 0)
    afternoon_state = sim.step(dt_minutes=1.0)
    afternoon_outdoor = afternoon_state.weather.outdoor_temperature_c

    # Afternoon must be substantially hotter than early morning
    assert afternoon_outdoor > morning_outdoor + 5.0
    assert 20.0 <= morning_outdoor <= 28.0
    assert 28.0 <= afternoon_outdoor <= 40.0


def test_4_occupancy_changes_according_to_schedule(sim):
    """Test 4: Occupancy changes dynamically with time of day."""
    # Night (03:00): Sleeping in bedroom
    sim.current_time = datetime.datetime(2026, 6, 15, 3, 0, 0)
    night_state = sim.step(dt_minutes=0.0)
    assert night_state.occupancy.is_occupied is True
    assert night_state.occupancy.room_occupancy["bedroom"] > 0
    assert night_state.occupancy.room_occupancy["kitchen"] == 0

    # Daytime work hours (12:00): Low/empty occupancy
    sim.current_time = datetime.datetime(2026, 6, 15, 12, 0, 0)
    day_state = sim.step(dt_minutes=0.0)
    assert day_state.occupancy.room_occupancy["bedroom"] == 0
    assert day_state.occupancy.total_occupants <= 1


def test_5_appliance_power_included_in_total_consumption(sim):
    """Test 5: Turning on appliances accurately sums into total household load."""
    # Temporarily turn off cycling refrigerator to isolate deterministic additive power
    sim.appliances.appliances["refrigerator"].status = "OFF"
    sim.appliances.appliances["refrigerator"].power_watts = 0.0

    base_state = sim.get_current_home_state()
    base_load = base_state.total_load_watts

    # Turn on TV (120W) and Living Room Light (15W)
    sim.turn_appliance_on("tv_living_room")
    sim.turn_appliance_on("lights_living_room")
    new_state = sim.step(dt_minutes=1.0)

    expected_increase = 120.0 + 15.0
    assert abs((new_state.total_load_watts - base_load) - expected_increase) < 1.0


def test_6_ac_operation_affects_room_temperature(sim):
    """Test 6: AC operation cools the room and extracts moisture."""
    sim.change_temperature("living_room", 30.0)
    sim.change_weather(WeatherCondition.HOT, temp_c=34.0, humidity_pct=60.0)
    
    # 1. Without AC: Room heats up or stays hot
    sim.turn_appliance_off("ac_living_room")
    state_no_ac = sim.step(dt_minutes=30.0)
    temp_no_ac = state_no_ac.rooms["living_room"].temperature_c

    # 2. Reset and turn AC ON at 1500W, setpoint 22°C
    sim.change_temperature("living_room", 30.0)
    sim.execute_appliance_action("ac_living_room", "ON", power_watts=1500.0, setpoint_c=22.0)
    state_with_ac = sim.step(dt_minutes=30.0)
    temp_with_ac = state_with_ac.rooms["living_room"].temperature_c

    # AC must actively reduce temperature compared to uncooled state
    assert temp_with_ac < temp_no_ac
    assert temp_with_ac < 30.0


def test_7_tariff_changes_according_to_simulated_time(sim):
    """Test 7: Tariff tier and rate match configured TOU schedule."""
    # 03:00 -> OFF_PEAK (₹4)
    sim.current_time = datetime.datetime(2026, 6, 15, 3, 0, 0)
    s1 = sim.step(dt_minutes=0.0)
    assert s1.tariff.tier == TariffTier.OFF_PEAK
    assert s1.tariff.rate == 4.0

    # 10:00 -> NORMAL (₹8)
    sim.current_time = datetime.datetime(2026, 6, 15, 10, 0, 0)
    s2 = sim.step(dt_minutes=0.0)
    assert s2.tariff.tier == TariffTier.NORMAL
    assert s2.tariff.rate == 8.0

    # 19:00 -> PEAK (₹12)
    sim.current_time = datetime.datetime(2026, 6, 15, 19, 0, 0)
    s3 = sim.step(dt_minutes=0.0)
    assert s3.tariff.tier == TariffTier.PEAK
    assert s3.tariff.rate == 12.0


def test_8_energy_and_cost_calculations(sim):
    """Test 8: Energy (kWh) and electricity cost accumulate correctly over time."""
    # Fix time at 10:00 (NORMAL rate = ₹8.0/kWh)
    sim.current_time = datetime.datetime(2026, 6, 15, 10, 0, 0)
    sim.appliances.appliances["refrigerator"].status = "OFF"
    sim.appliances.appliances["refrigerator"].power_watts = 0.0

    # Turn on 1000W load for 60 minutes
    sim.execute_appliance_action("ac_living_room", "ON", power_watts=1000.0)
    sim.step(dt_minutes=60.0)

    state = sim.get_current_home_state()
    # 1000W for 1 hr = 1.0 kWh
    ac_app = state.appliances["ac_living_room"]
    assert abs(ac_app.total_energy_kwh - 1.0) < 0.05
    # Cost = 1.0 kWh * ₹8.0/kWh = ₹8.0
    assert abs(state.estimated_cost_accumulated - 8.0) < 0.5


def test_9_demo_scenarios_load_correctly(sim):
    """Test 9: All 7 demo scenarios load and initialize expected configurations."""
    for i in range(1, 8):
        scenario_id = f"SCENARIO_{i}"
        result = ScenarioRegistry.apply_scenario(scenario_id, sim)
        assert result["success"] is True, f"Failed loading scenario {scenario_id}: {result.get('error')}"

    # Verify specific details of Scenario 5 (High load)
    ScenarioRegistry.apply_scenario("SCENARIO_5_HIGH_ENERGY_LOAD", sim)
    state = sim.get_current_home_state()
    assert state.appliances["ac_living_room"].status == "ON"
    assert state.appliances["water_heater"].status == "ON"
    assert state.appliances["washing_machine"].status == "ON"
    assert state.total_load_watts >= 4300.0

    # Verify Scenario 6 (Anomaly)
    ScenarioRegistry.apply_scenario("SCENARIO_6_ENERGY_ANOMALY", sim)
    state = sim.get_current_home_state()
    assert state.appliances["washing_machine"].power_watts == 1700.0


def test_10_user_override_is_preserved(sim):
    """Test 10: Manual user override sets is_user_override and retains preference."""
    sim.execute_appliance_action(
        "ac_living_room",
        "ON",
        power_watts=1500.0,
        is_user_override=True
    )
    state = sim.get_current_home_state()
    ac = state.appliances["ac_living_room"]
    assert ac.is_user_override is True
    assert "ac_living_room" in state.active_overrides


def test_11_reset_returns_simulator_to_initial_state(sim):
    """Test 11: Reset restores simulation clock, costs, and default appliances."""
    # Dirty the state
    sim.step(dt_minutes=120.0)
    sim.turn_appliance_on("water_heater")
    sim.change_temperature("bedroom", 32.0)
    assert sim.cumulative_cost > 0.0

    # Reset
    sim.reset()
    clean_state = sim.get_current_home_state()
    assert clean_state.simulated_time == sim.initial_start_time
    assert clean_state.estimated_cost_accumulated == 0.0
    assert clean_state.appliances["water_heater"].status == "OFF"
    assert clean_state.active_scenario is None


def test_12_invalid_appliance_actions_rejected_safely(sim):
    """Test 12: Invalid appliance actions return error dictionary without crashing."""
    # Unknown appliance ID
    res1 = sim.execute_appliance_action("non_existent_gadget", "ON")
    assert res1["success"] is False
    assert "error" in res1

    # Unsupported action verb
    res2 = sim.execute_appliance_action("ac_living_room", "EXPLODE")
    assert res2["success"] is False
    assert "error" in res2

    # Negative power argument
    res3 = sim.execute_appliance_action("ac_living_room", "SET_POWER", power_watts=-500.0)
    assert res3["success"] is False
