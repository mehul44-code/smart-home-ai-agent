# Prompt 4 agent audit

## Existing architecture

The existing `backend/app/agent/` package has seven stage-oriented modules:
`perception.py`, `prediction.py`, `reasoning.py`, `decision.py`, `action.py`,
`feedback.py`, and `explanation.py`, orchestrated by `core.py`.

## Existing functionality

- The simulator facade exposes current state and appliance actions.
- Perception flattens a legacy simulator dictionary.
- Prediction delegates thermal estimates to the existing model manager.
- Reasoning creates four AC profiles and ranks a hard-coded loss.
- Decision selects the first profile and adds fixed secondary appliance commands.
- Action dispatches through the simulator facade.
- Feedback calculates a basic comfort/cost result.
- Explanation renders a textual rationale.
- `/api/agent/step` preserves the legacy seven-stage response and stores a
  legacy decision-log row.

## Incomplete or unsafe functionality

- Perception fabricates defaults and does not validate required sensor,
  occupancy, tariff, appliance, or power values.
- Prediction is coupled to the ML manager and has no replaceable baseline
  interface or comfort/occupancy/anomaly outputs.
- Candidate setpoints and power values do not come from the current simulator
  appliance.
- Reasoning uses fixed weights, hides score components, and has no complete
  safety filtering or user preference adaptation.
- Decision emits unsupported simulator actions such as `DEFER`, `CHARGE`, and
  `HEAT`, and can reverse manual overrides.
- Action ignores simulator failures and reports every command as applied.
- Feedback lacks before/after energy, comfort, and prediction-error fields.
- Agent decisions and feedback are not persisted in the required structured
  Prompt 3 tables; `/api/agent/status` reports disabled.

## Reusable data flow

```text
HomeState -> validated perception -> baseline prediction
-> candidate generation -> safety filtering -> utility scoring
-> simulator action -> observed HomeState -> feedback -> explanation
-> AgentDecision/FeedbackEvent persistence
```

The existing module boundaries, simulator safety layer, Prompt 3 database,
legacy response keys, and simulator tests will be preserved.
