from backend.app.agent.core import AutonomousAgent
from backend.app.agent.perception import PerceptionEngine
from backend.app.agent.reasoning import ReasoningEngine
from backend.app.simulator.home_simulator import simulator_instance
from backend.app.simulator.scenarios import ScenarioRegistry
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
    assert {candidate["id"] for candidate in candidates} == {"RUN_NOW", "DELAY", "SCHEDULE_FOR_OFF_PEAK"}


def test_water_heater_candidate_set():
    state, _ = _step("NORMAL_HOME")
    percept = PerceptionEngine().observe(state)
    candidates = ReasoningEngine().evaluate_appliance_candidates(percept, "water_heater")
    assert {candidate["id"] for candidate in candidates} == {"RUN_NOW", "DELAY"}


def test_peak_laundry_uses_future_tariff_and_does_not_run():
    state, result = _step("PEAK_TARIFF_LAUNDRY")
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


def test_washing_override_is_preserved():
    ScenarioRegistry.apply_scenario("NORMAL_HOME", simulator_instance.engine)
    simulator_instance.engine.execute_appliance_action(
        "washing_machine", "ON", power_watts=800, is_user_override=True
    )
    result = AutonomousAgent().step(simulator_instance.get_current_home_state().model_dump(mode="json"))
    decision = result["appliance_decisions"]["washing_machine"]
    assert decision["override_respected"] is True
    assert result["appliance_actions"]["washing_machine"]["details"] == {}


def test_result_keeps_all_ac_stages_and_adds_two_appliances():
    _, result = _step("NORMAL_HOME")
    assert all(f"stage_{number}_" in " ".join(result) for number in range(1, 8))
    assert set(result["appliance_decisions"]) == {"washing_machine", "water_heater"}


def test_scenario_aliases_are_available():
    for alias in ("PEAK_TARIFF_LAUNDRY", "peak tariff laundry", "HIGH_LOAD_WATER_HEATER"):
        response = client.post("/api/simulation/scenario", json={"scenario_id": alias})
        assert response.status_code == 200


def test_agent_history_exposes_feedback_and_decision_logs():
    response = client.post("/api/agent/step")
    assert response.status_code == 200
    assert client.get("/api/agent/feedback").json()["count"] >= 3
    assert client.get("/api/agent/decision-logs").json()["count"] >= 3
