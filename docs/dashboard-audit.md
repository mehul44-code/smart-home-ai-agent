# Prompt 6 dashboard audit

## Existing surface

The frontend is a Vite/React application in `frontend/src`. It previously
rendered a dark metrics header, a small appliance list, two charts, and a
7-stage agent JSON viewer. API calls were spread across the page and the old
socket client connected to the legacy `/ws/simulation` stream.

## Backend contracts used

The dashboard reads `/api/simulation/state`, `/api/status`, `/api/appliances`,
`/api/energy?limit=50`, `/api/tariff?limit=50`, `/api/preferences`,
`/api/agent/status`, `/api/agent/history`, and `/api/anomalies`. Commands use
`POST /api/agent/step`, `POST /api/appliances/{id}/action`,
`POST /api/override?appliance_id=`, `POST /api/preferences`, and
`POST /api/simulation/scenario`.

The live contract is `WS /ws/home`, emitting `connected`, `state_update`, and
`error` messages. The client reports connected, reconnecting, and disconnected
states and retries with bounded backoff.

## Prompt 6 gaps addressed

The new light dashboard centralizes requests, supports environment-configured
backend URLs, renders live home/room/device state, agent decisions and
explanations, prediction/feedback data, historical energy, anomalies, tariff
and preference controls, scenario buttons, and safe backend appliance actions.
Missing backend fields are shown as an explicit em dash/empty state rather than
invented values.
