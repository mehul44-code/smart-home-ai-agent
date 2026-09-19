# Multi-appliance autonomy audit

## Existing AC logic

`AutonomousAgent.step()` currently observes one simulator state, predicts
thermal/energy/comfort outcomes, evaluates the AC candidates `AC_OFF`,
`AC_ON_24`, `AC_ON_25`, and `AC_ON_26`, selects the lowest-loss safe candidate,
dispatches it through the simulator safety layer, observes the result, and
generates feedback and an explanation. `ReasoningEngine` owns configurable
comfort, energy, peak, and switching weights; `DecisionEngine` preserves an
active AC user override.

## Current appliance capabilities

The simulator exposes AC, washing machine, water heater, TV, lights, fan, and
refrigerator state with power, priority, runtime, and override fields.
`SimulationEngine.execute_appliance_action()` is the authoritative safety and
state-transition boundary. Existing REST controls and the dashboard already
route manual commands through that boundary. Tariff state includes current
tier/rate and the tariff model can calculate future periods.

## Reusable components

The new work should reuse `PerceptionEngine`'s normalized appliance state,
`ReasoningEngine`'s configurable utility conventions, `DecisionEngine`'s
override handling pattern, `ActionDispatcher`, `FeedbackEngine`, Prompt 3
`AgentDecision`/`FeedbackEvent` persistence, scenario registry, and the
existing dashboard/service layer. AC candidate generation and behavior must
remain unchanged.

## Washing machine additions

Add candidates for `RUN_NOW`, `DELAY`, and `SCHEDULE_FOR_OFF_PEAK`. Their
scores must use the current tariff, real future tariff information, load,
power, shiftability/priority, preferences, and override state. A selected
delay should be represented as a schedule decision without falsely claiming
the appliance ran. Feedback should include target tariff/rate, delay, cost
difference, and execution/scheduling status.

## Water heater additions

Add `RUN_NOW` and `DELAY` candidates using real simultaneous load, AC and
washing-machine power, tariff, priority, preferences, and overrides. Delaying
must reduce modeled peak impact when valid and must be dispatched/scheduled
through existing simulator actions rather than directly mutating state.
Feedback should capture load before/after, tariff, power impact, and success.

## Integration constraints

The implementation will extend the existing agent result with per-appliance
decision sections and preserve all seven AC stages, persistence endpoints,
WebSocket behavior, ML fallback, and dashboard design. TV, lights,
refrigerator, and fan remain non-autonomous.
