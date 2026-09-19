# Prompt 3 API

Run `python -m uvicorn backend.app.main:app --reload` from the repository
root. SQLite is initialized automatically. Set `DATABASE_URL` to change the
database location; the default is `sqlite+aiosqlite:///./smart_home.db`.

## Database

The simulator owns current state. The database stores history and persistent
records in these tables:

| Table | Purpose |
| --- | --- |
| `sensor_readings` | Room and sensor snapshots |
| `appliances` | Persisted appliance metadata/state snapshots |
| `appliance_events` | ON/OFF, setting, override, and invalid-action events |
| `agent_decisions` | Decisions explicitly supplied by a future caller |
| `energy_consumption` | Appliance and aggregate energy history |
| `tariff_history` | Tariff snapshots |
| `user_preferences` | Current validated preference record |
| `feedback_events` | Reserved feedback/audit storage |
| `anomalies` | Explicitly submitted anomaly records |

No route creates autonomous decisions or runs ML.

## GET endpoints

All REST routes use the `/api` prefix.

- `/api/sensors` returns live simulator sensors; `?limit=N` returns persisted readings.
- `/api/appliances` returns live appliance state from the simulator.
- `/api/energy` returns live aggregate energy; `?limit=N` adds history.
- `/api/tariff` returns the live tariff; `?limit=N` adds history.
- `/api/agent/status` reports that autonomous behavior is disabled.
- `/api/agent/history` returns supplied decision records.
- `/api/anomalies` returns persisted anomaly records.
- `/api/preferences` returns the persisted preference record.
- `/api/simulation/state` returns the complete live `HomeState`.
- `/api/status` returns compatibility health/status information.

## POST endpoints

- `/api/simulation/start`, `/pause`, `/reset` control the simulator clock.
- `/api/simulation/step` accepts `{"dt_minutes": 1}` and persists simulator history.
- `/api/simulation/scenario` accepts a registered scenario ID/name.
- `/api/appliances/{appliance_id}/action` validates and delegates actions to
  the simulator safety layer.
- `/api/override?appliance_id=...` applies a user override through the same
  simulator action path.
- `/api/preferences` validates and stores temperature, priorities, mode,
  manual override, and expiry.
- `/api/anomalies` stores explicit expected/actual power deviations.
- `/api/agent/decisions` stores caller-supplied decision JSON and does not
  generate a decision.

Invalid IDs/actions, malformed bodies, invalid preference values, unknown
scenarios, simulator validation failures, and database failures return an HTTP
error without exposing a traceback.

## WebSocket

Connect to `ws://127.0.0.1:8000/ws/home`. The first message is a `connected`
event, followed by `state_update` messages containing timestamp, simulated
time, rooms, humidity, occupancy, appliance state, total load, total energy,
and tariff data. A client may send `{"action":"step","dt_minutes":1}`,
`start`, `pause`, `reset`, or `state`. The endpoint only advances and reports
the simulator; it never invokes the autonomous agent loop.

The legacy `/ws/simulation` stream remains available for compatibility and is
also simulator-only during Prompt 3.
