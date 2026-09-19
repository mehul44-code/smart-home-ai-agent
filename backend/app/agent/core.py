from typing import Dict, Any, Optional
from backend.app.agent.perception import PerceptionEngine
from backend.app.agent.prediction import PredictionEngine
from backend.app.agent.reasoning import ReasoningEngine
from backend.app.agent.decision import DecisionEngine
from backend.app.agent.action import ActionDispatcher
from backend.app.agent.feedback import FeedbackEngine
from backend.app.agent.explanation import ExplanationEngine
from backend.app.simulator.home_simulator import simulator_instance


class AutonomousAgent:
    """
    Lead Orchestrator for the Autonomous Smart Home AI Agent.
    Executes the continuous 7-stage cognitive loop:
    1. PERCEPTION
    2. PREDICTION
    3. REASONING
    4. DECISION
    5. ACTION
    6. FEEDBACK
    7. EXPLANATION
    """

    def __init__(self):
        self.perception_engine = PerceptionEngine()
        self.prediction_engine = PredictionEngine()
        self.reasoning_engine = ReasoningEngine()
        self.decision_engine = DecisionEngine()
        self.action_dispatcher = ActionDispatcher()
        self.feedback_engine = FeedbackEngine()
        self.explanation_engine = ExplanationEngine()
        
        self.step_counter = 0
        self.last_prediction: Optional[Dict[str, Any]] = None

    def step(self, current_sim_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes one full iteration of the 7-stage cognitive loop.
        """
        self.step_counter += 1
        
        # 1. PERCEPTION
        if current_sim_state is None:
            current_sim_state = simulator_instance.step(dt_minutes=5.0)
            
        percept = self.perception_engine.observe(current_sim_state)

        # 2. PREDICTION
        prediction = self.prediction_engine.predict(percept)

        # 3. REASONING
        candidate_evaluations = self.reasoning_engine.evaluate_candidates(percept, prediction)

        # 4. DECISION
        decision = self.decision_engine.decide(percept, candidate_evaluations)

        # 5. ACTION
        action_result = self.action_dispatcher.dispatch(decision)

        # 6. FEEDBACK
        # Advance simulation slightly to capture physical consequence of action
        consequent_state = simulator_instance.step(dt_minutes=5.0)
        feedback = self.feedback_engine.evaluate(
            previous_prediction=prediction,
            observed_state=consequent_state,
            decision=decision
        )

        # 7. EXPLANATION
        explanation = self.explanation_engine.explain(
            percept=percept,
            prediction=prediction,
            decision=decision,
            feedback=feedback
        )

        self.last_prediction = prediction

        return {
            "step_id": self.step_counter,
            "timestamp": percept.get("timestamp"),
            "stage_1_perception": percept,
            "stage_2_prediction": prediction,
            "stage_3_reasoning": {
                "candidates_evaluated": candidate_evaluations,
                "preferred_candidate": candidate_evaluations[0]["id"]
            },
            "stage_4_decision": decision,
            "stage_5_action": action_result,
            "stage_6_feedback": feedback,
            "stage_7_explanation": explanation,
            "consequent_state": consequent_state
        }


# Singleton agent instance
agent_instance = AutonomousAgent()
