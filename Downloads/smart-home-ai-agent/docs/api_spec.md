# API & WebSocket Specification

## REST API Endpoints

### 1. Health & Status
- **`GET /api/status`**
  - **Description**: Returns agent status, simulator time, and system health.
  - **Response (200 OK)**:
    ```json
    {
      "status": "online",
      "simulation_time": "2026-06-15T14:15:00Z",
      "agent_mode": "AUTONOMOUS",
      "active_appliances": 4
    }
    ```

### 2. Appliances
- **`GET /api/appliances`**
  - **Description**: Lists all monitored appliances with state, power, and priorities.
- **`POST /api/appliances/{id}/override`**
  - **Description**: User manual override for appliance state.

### 3. Agent Execution
- **`POST /api/agent/step`**
  - **Description**: Executes a single step of the 7-stage cognitive loop manually or triggers on schedule.
  - **Response (200 OK)**:
    ```json
    {
      "step_id": 42,
      "timestamp": "2026-06-15T14:15:00Z",
      "perception": { ... },
      "prediction": { ... },
      "reasoning": { ... },
      "decision": { ... },
      "action": { ... },
      "feedback": { ... },
      "explanation": "..."
    }
    ```

### 4. Telemetry History
- **`GET /api/history?limit=100`**
  - **Description**: Returns historical energy consumption, temperature, and tariff metrics for charting.

---

## WebSocket Stream

### Endpoint: `ws://localhost:8000/ws/simulation`
- **Protocol**: JSON messages over WebSocket.
- **Events Emitted**:
  - `telemetry_update`: Real-time sensor readings and energy metrics every simulation tick.
  - `agent_step`: Detailed output from each phase of the 7-stage loop.
  - `appliance_state_change`: State change notification.
