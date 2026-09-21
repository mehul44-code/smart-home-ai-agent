from backend.app.agent.core import AutonomousAgent
from backend.app.agent.perception import PerceptionEngine
from backend.app.agent.reasoning import ReasoningEngine
from backend.app.simulator.home_simulator import simulator_instance
from backend.app.simulator.appliances import PriorityLevel
from backend.app.simulator.scenarios import ScenarioRegistry
from backend.app.simulator.tariff import TariffTier
from backend.app.main import app
from fastapi.testclient import TestClient


client = TestClient(app)


def _step(scenario):
    ScenarioRegistry.apply_scenario(scenario, simulator_instance.engine)
    state = simulator_instance.get_current_home_state()
    result = AutonomousAgent().step(state.model_dump(mode="json"))
    return state, result


def test_washing_machine_candidate_set():
    state, _ = _step("NORMAL_HOME")
    percept = PerceptionEngine().observe(state)
    candidates = ReasoningEngine().evaluate_appliance_candidates(percept, "washing_machine")
    assert {candidate["id"] for candidate in candidates} == {"NO_OP"}


def test_washing_machine_no_demand_returns_idle():
    ScenarioRegistry.apply_scenario("NORMAL_HOME", simulator_instance.engine)
    result = AutonomousAgent().step(simulator_instance.get_current_home_state().model_dump(mode="json"))
    decision = result["appliance_decisions"]["washing_machine"]
    assert decision["chosen_strategy"] == "NO_OP"
    assert "No washing-machine demand is active" in decision["reason"]
    assert result["appliance_actions"]["washing_machine"]["execution_status"] == "NO_OP"


def test_water_heater_candidate_set():
    state, _ = _step("NORMAL_HOME")
    percept = PerceptionEngine().observe(state)
    candidates = ReasoningEngine().evaluate_appliance_candidates(percept, "water_heater")
    assert {candidate["id"] for candidate in candidates} == {"NO_OP"}


def test_agent_step_uses_single_snapshot_for_all_decisions():
    ScenarioRegistry.apply_scenario("HIGH_LOAD_WATER_HEATER", simulator_instance.engine)
    state = simulator_instance.get_current_home_state()
    result = AutonomousAgent().step(state.model_dump(mode="json"))
    cycle_id = result["decision_cycle_id"]
    assert result["snapshot_timestamp"] == result["stage_1_perception"]["timestamp"]
    assert result["snapshot"]["timestamp"] == result["snapshot_timestamp"]
    assert result["stage_4_decision"]["decision_cycle_id"] == cycle_id
    for appliance_id in ("washing_machine", "water_heater"):
        decision = result["appliance_decisions"][appliance_id]
        assert decision["decision_cycle_id"] == cycle_id
        assert decision["snapshot_timestamp"] == result["snapshot_timestamp"]
        assert decision["load_before_kw"] == result["snapshot"]["total_load_watts"] / 1000.0


def test_water_heater_current_and_candidate_power_are_separate():
    ScenarioRegistry.apply_scenario("NORMAL_HOME", simulator_instance.engine)
    simulator_instance.engine.change_tariff(TariffTier.OFF_PEAK, rate=4.0)
    simulator_instance.engine.appliances.execute_action("water_heater", "ON", power_watts=2000.0)
    state = simulator_instance.get_current_home_state()
    result = AutonomousAgent().step(state.model_dump(mode="json"))
    heater = result["appliance_decisions"]["water_heater"]
    assert heater["load_before_kw"] >= 0.0
    assert heater["heater_addition_kw"] > 0.0
    assert heater["current_tariff_rate"] == result["stage_1_perception"]["current_tariff_rate"]
    assert heater["current_cost"] >= 0.0


def test_water_heater_no_demand_returns_idle():
    ScenarioRegistry.apply_scenario("NORMAL_HOME", simulator_instance.engine)
    state = simulator_instance.get_current_home_state()
    assert state.appliances["water_heater"].status == "OFF"
    result = AutonomousAgent().step(state.model_dump(mode="json"))
    decision = result["appliance_decisions"]["water_heater"]
    assert decision["chosen_strategy"] == "NO_OP"
    assert "No water-heating demand is active" in decision["reason"]
    assert result["appliance_actions"]["water_heater"]["execution_status"] == "NO_OP"
    assert result["appliance_candidates"]["water_heater"][0]["id"] == "NO_OP"


def test_water_heater_runs_now_when_real_demand_and_low_load():
    ScenarioRegistry.apply_scenario("NORMAL_HOME", simulator_instance.engine)
    simulator_instance.engine.change_tariff(TariffTier.OFF_PEAK, rate=4.0)
    simulator_instance.engine.appliances.execute_action("water_heater", "ON", power_watts=2000.0)
    result = AutonomousAgent().step(simulator_instance.get_current_home_state().model_dump(mode="json"))
    decision = result["appliance_decisions"]["water_heater"]
    assert decision["chosen_strategy"] == "RUN_NOW"
    assert decision["reason"].lower().find("water-heater") >= 0 or "run now" in decision["reason"].lower()


def test_water_heater_delay_when_real_demand_and_high_load():
    ScenarioRegistry.apply_scenario("HIGH_LOAD_WATER_HEATER", simulator_instance.engine)
    result = AutonomousAgent().step(simulator_instance.get_current_home_state().model_dump(mode="json"))
    decision = result["appliance_decisions"]["water_heater"]
    assert decision["chosen_strategy"] == "DELAY"
    assert decision["delay_minutes"] >= 0


def test_occupancy_reasoning_cannot_report_unoccupied_when_occupants_are_present():
    ScenarioRegistry.apply_scenario("HOT_OCCUPIED_ROOM", simulator_instance.engine)
    result = AutonomousAgent().step(simulator_instance.get_current_home_state().model_dump(mode="json"))
    percept = result["stage_1_perception"]
    assert percept["occupancy"] is True
    assert percept["occupant_count"] > 0
    assert "unoccupied" not in result["stage_7_explanation"].lower()


def test_peak_laundry_uses_future_tariff_and_does_not_run():
    state, result = _step("PEAK_TARIFF_LAUNDRY")
    assert state.appliances["washing_machine"].status == "ON"
    assert state.appliances["washing_machine"].power_watts == 800.0
    decision = result["appliance_decisions"]["washing_machine"]
    assert decision["chosen_strategy"] in {"DELAY", "SCHEDULE_FOR_OFF_PEAK"}
    assert decision["schedule"]["target_rate"] == 4.0
    assert result["appliance_actions"]["washing_machine"]["execution_status"] == "SCHEDULED"
    assert result["consequent_state"]["appliances"]["washing_machine"]["status"] == state.appliances["washing_machine"].status


def test_high_load_water_heater_reduces_modeled_peak():
    _, result = _step("HIGH_LOAD_WATER_HEATER")
    decision = result["appliance_decisions"]["water_heater"]
    assert decision["chosen_strategy"] == "DELAY"
    assert decision["load_after_kw"] <= decision["load_before_kw"]
    assert result["appliance_actions"]["water_heater"]["details"] == {}


def test_washing_machine_runs_now_when_current_tariff_is_already_favorable():
    ScenarioRegistry.apply_scenario("NORMAL_HOME", simulator_instance.engine)
    simulator_instance.engine.change_tariff(TariffTier.OFF_PEAK, rate=4.0)
    simulator_instance.engine.appliances.execute_action("washing_machine", "ON", power_watts=800.0)
    state = simulator_instance.get_current_home_state()
    result = AutonomousAgent().step(state.model_dump(mode="json"))
    assert result["appliance_decisions"]["washing_machine"]["chosen_strategy"] == "RUN_NOW"
    assert all(candidate["id"] != "SCHEDULE_FOR_OFF_PEAK" or not candidate["safe"]
               for candidate in result["appliance_candidates"]["washing_machine"])


def test_washing_machine_high_priority_can_run_now_when_waiting_is_not_required():
    ScenarioRegistry.apply_scenario("NORMAL_HOME", simulator_instance.engine)
    simulator_instance.engine.change_tariff(TariffTier.PEAK, rate=8.0)
    simulator_instance.engine.appliances.appliances["washing_machine"].priority = PriorityLevel.HIGH
    simulator_instance.engine.appliances.execute_action("washing_machine", "ON", power_watts=800.0)
    state = simulator_instance.get_current_home_state()
    result = AutonomousAgent().step(state.model_dump(mode="json"))
    decision = result["appliance_decisions"]["washing_machine"]
    assert decision["chosen_strategy"] == "RUN_NOW"
    assert decision["priority"] == "HIGH"


def test_water_heater_runs_now_when_load_is_low_and_peak_is_safe():
    ScenarioRegistry.apply_scenario("NORMAL_HOME", simulator_instance.engine)
    simulator_instance.engine.change_tariff(TariffTier.OFF_PEAK, rate=4.0)
    simulator_instance.engine.appliances.execute_action("water_heater", "ON", power_watts=2000.0)
    state = simulator_instance.get_current_home_state()
    result = AutonomousAgent().step(state.model_dump(mode="json"))
    assert result["appliance_decisions"]["water_heater"]["chosen_strategy"] == "RUN_NOW"


def test_decision_diversity_regression_keeps_run_now_and_delay_available():
    ScenarioRegistry.apply_scenario("NORMAL_HOME", simulator_instance.engine)
    simulator_instance.engine.change_tariff(TariffTier.OFF_PEAK, rate=4.0)
    simulator_instance.engine.appliances.execute_action("washing_machine", "ON", power_watts=800.0)
    off_peak_state = simulator_instance.get_current_home_state()
    off_peak = AutonomousAgent().step(off_peak_state.model_dump(mode="json"))

    ScenarioRegistry.apply_scenario("PEAK_TARIFF_LAUNDRY", simulator_instance.engine)
    peak_state = simulator_instance.get_current_home_state()
    peak = AutonomousAgent().step(peak_state.model_dump(mode="json"))

    selected = {
        off_peak["appliance_decisions"]["washing_machine"]["chosen_strategy"],
        peak["appliance_decisions"]["washing_machine"]["chosen_strategy"],
    }
    assert {"RUN_NOW", "DELAY"}.issubset(selected)


def test_appliance_decisions_share_snapshot_load_tariff_and_occupancy():
    ScenarioRegistry.apply_scenario("HOT_OCCUPIED_ROOM", simulator_instance.engine)
    state = simulator_instance.get_current_home_state()
    result = AutonomousAgent().step(state.model_dump(mode="json"))
    snapshot = result["snapshot"]
    percept = result["stage_1_perception"]
    snapshot_occupancy = snapshot.get("occupancy_detail", snapshot.get("occupancy", {}))
    assert percept["occupant_count"] == snapshot_occupancy["total_occupants"]
    assert percept["total_load_watts"] == snapshot["total_load_watts"]
    assert percept["current_tariff_rate"] == snapshot["tariff"]["rate"]
    for decision in result["appliance_decisions"].values():
        assert decision["load_before_kw"] == snapshot["total_load_watts"] / 1000.0
        assert decision["current_tariff_rate"] == snapshot["tariff"]["rate"]


def test_washing_override_is_preserved():
    ScenarioRegistry.apply_scenario("NORMAL_HOME", simulator_instance.engine)
    simulator_instance.engine.execute_appliance_action(
        "washing_machine", "ON", power_watts=800, is_user_override=True
    )
    result = AutonomousAgent().step(simulator_instance.get_current_home_state().model_dump(mode="json"))
    decision = result["appliance_decisions"]["washing_machine"]
    assert decision["override_respected"] is True
    assert result["appliance_actions"]["washing_machine"]["details"] == {}


def test_washing_machine_off_override_returns_idle_without_scheduling():
    ScenarioRegistry.apply_scenario("NORMAL_HOME", simulator_instance.engine)
    simulator_instance.engine.execute_appliance_action(
        "washing_machine", "OFF", power_watts=0, is_user_override=True
    )
    result = AutonomousAgent().step(simulator_instance.get_current_home_state().model_dump(mode="json"))
    decision = result["appliance_decisions"]["washing_machine"]
    assert decision["chosen_strategy"] == "NO_OP"
    assert decision["override_respected"] is True
    assert decision["schedule"] is None


def test_result_keeps_all_ac_stages_and_adds_two_appliances():
    _, result = _step("NORMAL_HOME")
    assert all(f"stage_{number}_" in " ".join(result) for number in range(1, 8))
    assert set(result["appliance_decisions"]) == {"washing_machine", "water_heater"}


def test_scenario_aliases_are_available():
    for alias in ("PEAK_TARIFF_LAUNDRY", "OFF_PEAK_LAUNDRY", "peak tariff laundry", "HIGH_LOAD_WATER_HEATER"):
        response = client.post("/api/simulation/scenario", json={"scenario_id": alias})
        assert response.status_code == 200


def test_off_peak_laundry_scenario_selects_run_now():
    response = client.post("/api/simulation/scenario", json={"scenario_id": "OFF_PEAK_LAUNDRY"})
    assert response.status_code == 200
    result = client.post("/api/agent/step")
    assert result.status_code == 200
    payload = result.json()
    assert payload["stage_1_perception"]["current_tariff_rate"] == 4.0
    assert payload["appliance_decisions"]["washing_machine"]["chosen_strategy"] == "RUN_NOW"


def test_high_priority_laundry_scenario_selects_run_now():
    response = client.post("/api/simulation/scenario", json={"scenario_id": "HIGH_PRIORITY_LAUNDRY"})
    assert response.status_code == 200
    result = client.post("/api/agent/step")
    assert result.status_code == 200
    decision = result.json()["appliance_decisions"]["washing_machine"]
    assert decision["priority"] == "HIGH"
    assert decision["chosen_strategy"] == "RUN_NOW"


def test_scenario_then_agent_step_uses_latest_scenario_snapshot():
    before = client.get("/api/agent/status").json()["step_count"]
    scenario = client.post("/api/simulation/scenario", json={"scenario_id": "PEAK_TARIFF_LAUNDRY"})
    assert scenario.status_code == 200
    state = scenario.json()["state_snapshot"]
    result = client.post("/api/agent/step")
    assert result.status_code == 200
    payload = result.json()
    assert client.get("/api/agent/status").json()["step_count"] == before + 1
    assert payload["snapshot_timestamp"] == state["timestamp"]
    assert payload["stage_1_perception"]["current_tariff_rate"] == state["tariff"]["rate"]
    assert payload["appliance_decisions"]["washing_machine"]["chosen_strategy"] in {"DELAY", "SCHEDULE_FOR_OFF_PEAK"}


def test_agent_history_exposes_feedback_and_decision_logs():
    response = client.post("/api/agent/step")
    assert response.status_code == 200
    assert client.get("/api/agent/feedback").json()["count"] >= 3
    assert client.get("/api/agent/decision-logs").json()["count"] >= 3
