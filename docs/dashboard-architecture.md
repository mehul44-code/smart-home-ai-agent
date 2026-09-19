# Dashboard architecture

The frontend is intentionally a thin client of the existing simulator and
agent:

* `src/services/api.js` is the single REST boundary. It applies the optional
  `VITE_BACKEND_URL`, a request timeout, JSON handling, and useful API errors.
* `src/services/websocket.js` owns the `/ws/home` connection, event dispatch,
  status transitions, and reconnect backoff.
* `DashboardPage` owns a refreshable read model. REST hydrates the page and
  WebSocket state updates replace the current simulator snapshot without
  pretending that a command succeeded.
* Agent step, appliance, preference, and scenario mutations call the backend
  and then refresh. This preserves the backend as the source of truth.
* Recharts only receives records returned by `/api/energy`; no placeholder
  points are generated.

The visual hierarchy puts current home state and the autonomous decision loop
first, followed by rooms and controls, analytics, predictions, alerts, and
competition scenarios. The six-stage timeline mirrors the available
perception/prediction/reasoning/decision/action/feedback data (the returned
explanation is displayed alongside it).
