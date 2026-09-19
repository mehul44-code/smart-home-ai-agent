import pytest
from fastapi.testclient import TestClient

from backend.app.agent.core import AutonomousAgent
from backend.app.agent.perception import PerceptionEngine
from backend.app.agent.prediction import PredictionEngine
from backend.app.main import app
from backend.app.simulator.home_simulator import simulator_instance
from backend.app.simulator.scenarios import ScenarioRegistry


client = TestClient(app)


def test_perception_is_authoritative_and_validated():
    state = simulator_instance.get_current_home_state()
    percept = PerceptionEngine().observe(state)
    assert percept["indoor_temp_c"] == state.rooms["living_room"].temperature_c
    assert percept["total_energy_kwh"] == state.total_energy_kwh
    invalid = state.model_dump(mode="json")
    invalid["rooms"]["living_room"]["temperature_c"] = 100
    with pytest.raises(ValueError):
        PerceptionEngine().observe(invalid)


def test_prediction_is_deterministic_baseline_with_required_outputs():
    result = AutonomousAgent().step()
    prediction = result["stage_2_prediction"]
    assert prediction["model"] == "deterministic_baseline"
    assert {"cooling_energy_needed_kwh", "expected_energy_consumption_kwh",
            "comfort_score", "occupancy", "anomaly_score"} <= prediction.keys()


def test_prediction_interface_accepts_future_injected_predictor():
    engine = PredictionEngine(predictor=lambda percept: {
        "cooling_energy_needed_kwh": 0.5,
        "comfort_score": 80,
        "occupancy": percept["occupant_count"],
    })
    percept = PerceptionEngine().observe(simulator_instance.get_current_home_state())
    prediction = engine.predict(percept)
    assert prediction["model"] == "injected_predictor"
    assert prediction["cooling_energy_needed_kwh"] == 0.5


def test_hot_room_evaluates_all_candidates_and_utility_components():
    ScenarioRegistry.apply_scenario("HOT_OCCUPIED_ROOM", simulator_instance.engine)
    result = AutonomousAgent().step()
    candidates = result["stage_3_reasoning"]["candidates_evaluated"]
    assert {"AC_OFF", "AC_ON_24", "AC_ON_25", "AC_ON_26"} <= {c["id"] for c in candidates}
    fields = {"comfort_benefit", "expected_energy_kwh", "hourly_cost_usd",
              "peak_load_impact_kw", "switching_penalty", "total_utility", "safe"}
    assert all(fields <= candidate.keys() for candidate in candidates)


@pytest.mark.parametrize("scenario", [
    "NORMAL_HOME", "HOT_OCCUPIED_ROOM", "EMPTY_ROOM", "PEAK_TARIFF",
    "HIGH_ENERGY_LOAD", "ENERGY_ANOMALY", "USER_OVERRIDE",
])
def test_required_scenarios_complete_full_loop(scenario):
    ScenarioRegistry.apply_scenario(scenario, simulator_instance.engine)
    result = AutonomousAgent().step()
    assert result["stage_1_perception"]["active_scenario"] is not None
    assert result["stage_5_action"]["success"] is True
    assert "prediction_error_c" in result["stage_6_feedback"]
    assert "energy_delta_kwh" in result["stage_6_feedback"]
    assert result["stage_7_explanation"]


def test_user_override_is_preserved():
    ScenarioRegistry.apply_scenario("USER_OVERRIDE", simulator_instance.engine)
    result = AutonomousAgent().step()
    assert result["stage_4_decision"]["override_respected"] is True
    assert result["stage_4_decision"]["actions"]["ac_living_room"]["status"] == "ON"


def test_agent_api_persists_decision_feedback_and_uses_preferences():
    ScenarioRegistry.apply_scenario("HOT_OCCUPIED_ROOM", simulator_instance.engine)
    response = client.post("/api/preferences", json={
        "preferred_temperature": 26,
        "comfort_priority": 0.2,
        "energy_priority": 0.8,
        "selected_mode": "ENERGY_SAVING",
    })
    assert response.status_code == 200
    response = client.post("/api/agent/step")
    assert response.status_code == 200
    result = response.json()
    assert result["stage_1_perception"]["preferences"]["selected_mode"] == "ENERGY_SAVING"
    assert client.get("/api/agent/status").json()["status"] == "ready"
    assert client.get("/api/agent/history").json()["count"] >= 1
