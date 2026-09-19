import copy
from typing import Any, Dict, Optional

from backend.app.agent.action import ActionDispatcher
from backend.app.agent.decision import DecisionEngine
from backend.app.agent.explanation import ExplanationEngine
from backend.app.agent.feedback import FeedbackEngine
from backend.app.agent.perception import PerceptionEngine
from backend.app.agent.prediction import PredictionEngine
from backend.app.agent.reasoning import ReasoningEngine
from backend.app.simulator.home_simulator import simulator_instance


class AutonomousAgent:
    def __init__(self):
        self.perception_engine = PerceptionEngine()
        self.prediction_engine = PredictionEngine()
        self.reasoning_engine = ReasoningEngine()
        self.decision_engine = DecisionEngine()
        self.action_dispatcher = ActionDispatcher()
        self.feedback_engine = FeedbackEngine()
        self.explanation_engine = ExplanationEngine()
        self.step_counter = 0
        self.last_result: Optional[Dict[str, Any]] = None

    def step(self, current_sim_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.step_counter += 1
        state = current_sim_state or simulator_instance.get_current_home_state()
        snapshot = copy.deepcopy(state)
        if hasattr(snapshot, "model_dump"):
            snapshot = snapshot.model_dump(mode="json")
        percept = self.perception_engine.observe(state)
        prediction = self.prediction_engine.predict(percept)
        candidates = self.reasoning_engine.evaluate_candidates(percept, prediction)
        decision = self.decision_engine.decide(percept, candidates)
        decision["decision_cycle_id"] = f"cycle_{self.step_counter}_{percept['timestamp']}"
        decision["snapshot_timestamp"] = percept["timestamp"]
        decision["simulator_state_version"] = f"{percept['timestamp']}|{len(snapshot.get('appliances', {}))}"
        action = self.action_dispatcher.dispatch(decision)
        decision["action_success"] = action["success"]
        appliance_decisions = {}
        appliance_candidates = {}
        appliance_actions = {}
        for appliance_id in ("washing_machine", "water_heater"):
            candidates_for_app = self.reasoning_engine.evaluate_appliance_candidates(percept, appliance_id)
            app_decision = self.decision_engine.decide_appliance(percept, candidates_for_app, appliance_id)
            app_decision["decision_cycle_id"] = decision["decision_cycle_id"]
            app_decision["snapshot_timestamp"] = percept["timestamp"]
            app_decision["simulator_state_version"] = decision["simulator_state_version"]
            app_action = self.action_dispatcher.dispatch(app_decision)
            app_decision["action_success"] = app_action["success"]
            appliance_decisions[appliance_id] = app_decision
            appliance_candidates[appliance_id] = candidates_for_app
            appliance_actions[appliance_id] = app_action
        consequent = simulator_instance.engine.step(dt_minutes=5.0)
        observed = self.perception_engine.observe(consequent)
        feedback = self.feedback_engine.evaluate(prediction, observed, decision, percept)
        explanation = self.explanation_engine.explain(percept, prediction, decision, feedback)
        result = {
            "step_id": self.step_counter,
            "timestamp": percept["timestamp"],
            "decision_cycle_id": f"cycle_{self.step_counter}_{percept['timestamp']}",
            "snapshot_timestamp": percept["timestamp"],
            "simulator_state_version": f"{percept['timestamp']}|{len(snapshot.get('appliances', {}))}",
            "snapshot": snapshot,
            "stage_1_perception": percept,
            "stage_2_prediction": prediction,
            "stage_3_reasoning": {"candidates_evaluated": candidates, "preferred_candidate": candidates[0]["id"]},
            "stage_4_decision": decision,
            "stage_5_action": action,
            "stage_6_feedback": feedback,
            "stage_7_explanation": explanation,
            "appliance_decisions": appliance_decisions,
            "appliance_candidates": appliance_candidates,
            "appliance_actions": appliance_actions,
            "consequent_state": consequent.model_dump(mode="json"),
        }
        self.last_result = result
        return result


agent_instance = AutonomousAgent()
