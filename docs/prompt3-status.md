# Prompt 3 implementation status

## Audit baseline

The repository already contains the Prompt 2 multi-room simulator and a partial
Prompt 3 backend. The simulator remains the source of current state through
`SimulationEngine.get_current_home_state()` and the facade
`simulator_instance.get_current_home_state()`.

## Complete

- SQLAlchemy async SQLite foundation with automatic `create_all()` startup.
- History-oriented models for sensor readings, appliances, appliance events,
  energy, tariffs, preferences, anomalies, feedback, and supplied agent
  decisions.
- Existing simulator scenarios, safety validation, state transitions, energy
  accounting, and Prompt 2 simulator tests are present.
- Basic REST routes for current simulation state, sensors, appliances, energy,
  tariff, agent status/history, anomalies, and preferences.
- Simulation start, pause, reset, step, scenario, appliance action,
  preferences, override, anomaly, and supplied-decision routes exist in part.

## Partial

- Existing database models include legacy `telemetry_records` and
  `agent_decision_logs` tables in addition to the required schema, and several
  required field names/types do not match the Prompt 3 contract.
- History persistence is only wired to simulation steps, scenarios, and
  successful appliance actions; reset/start/pause and invalid actions are not
  consistently audited.
- Request models provide useful bounds, but response models are absent and
  simulator/database exceptions are not consistently translated.
- `/api` route coverage exists, but response shapes and validation need to be
  made consistent and the override route should use the required appliance path
  form.
- The database URL is settings-driven, but initialization is coupled to every
  database dependency call and lacks a clean test/configuration lifecycle.
- Existing WebSocket code streams `/ws/simulation` and invokes the future agent
  loop; the required `/ws/home` simulator-only stream is missing.
- Existing API tests cover only legacy root/status/appliances/agent-step
  behavior.

## Completed after the audit

- Added the required `/ws/home` stream with serialized live state, client
  controls, periodic updates, and no autonomous agent invocation.
- Kept `/ws/simulation` for compatibility while removing implicit agent-loop
  execution from its stream.
- Aligned anomaly and agent-decision persistence fields with the Prompt 3
  contract and added structured JSON storage.
- Added comprehensive API/database/WebSocket regression coverage in
  `backend/tests/test_prompt3.py`.
- Added `docs/api.md` and replaced the placeholder README with startup,
  configuration, endpoint, database, WebSocket, and test documentation.
- Simulation controls now persist state snapshots and translate database
  failures to safe HTTP responses.

## Remaining scope boundary

The legacy `telemetry_records` and `agent_decision_logs` ORM classes remain for
backward compatibility with the existing `/api/agent/step` endpoint and are
not used by Prompt 3 routes. Prompt 4 agent reasoning, candidate scoring, ML,
prediction, feedback learning, and dashboard work remain intentionally
unimplemented.
