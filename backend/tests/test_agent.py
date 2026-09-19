import pytest
from backend.app.agent.core import agent_instance
from backend.app.simulator.home_simulator import simulator_instance


def test_agent_7_stage_step():
    """Verify that the agent completes all 7 stages and returns the structured schema."""
    result = agent_instance.step()

    assert "step_id" in result
    assert "stage_1_perception" in result
    assert "stage_2_prediction" in result
    assert "stage_3_reasoning" in result
    assert "stage_4_decision" in result
    assert "stage_5_action" in result
    assert "stage_6_feedback" in result
    assert "stage_7_explanation" in result

    # Verify stage details
    percept = result["stage_1_perception"]
    assert "indoor_temp_c" in percept
    assert "current_tariff_rate" in percept

    pred = result["stage_2_prediction"]
    assert "cooling_energy_needed_kwh" in pred

    decision = result["stage_4_decision"]
    assert "chosen_strategy" in decision
    assert "actions" in decision

    explanation = result["stage_7_explanation"]
    assert isinstance(explanation, str)
    assert len(explanation) > 20
