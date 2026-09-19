# Prompt 4 agent architecture

The agent extends the existing seven-stage foundation without creating a
second simulator or database:

```text
HomeState
  -> validated PerceptionEngine
  -> deterministic baseline PredictionEngine
  -> candidate generation and safety filtering
  -> configurable utility scoring
  -> DecisionEngine
  -> simulator safety layer
  -> observed HomeState and FeedbackEngine
  -> explanation and Prompt 3 persistence
```

`PerceptionEngine` reads the simulator's authoritative `HomeState`. It
normalizes rooms, weather, occupancy, appliances, load, energy, tariff,
preferences, and active overrides and rejects invalid values.

`PredictionEngine` is explicitly labelled `deterministic_baseline`. It
provides cooling requirement, expected energy, comfort score, occupancy, and a
simple anomaly score. A future model can be injected with
`PredictionEngine(predictor=...)`; no Prompt 5 ML behavior is enabled.

`ReasoningEngine` evaluates AC OFF, 24°C, 25°C, and 26°C candidates. It
exposes comfort benefit, predicted temperature effect, expected energy, tariff
cost, peak impact, switching penalty, preference/priority terms, total utility,
and safety validity. User overrides are hard preservation constraints.

The action dispatcher calls `SimulationEngine.execute_appliance_action()` and
reports its real result. Feedback compares before/after temperature, comfort,
energy, and the baseline prediction. `/api/agent/step` persists an
`AgentDecision`, `FeedbackEvent`, and agent appliance event.

The comfort score is a deterministic project-level simulation score, not a
medical measurement.
