import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.config import settings


client = TestClient(app)


def test_database_initialization_has_required_tables():
    client.get("/api/simulation/state")
    db_path = Path(settings.SYNC_DATABASE_URL.removeprefix("sqlite:///"))
    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {
        "sensor_readings",
        "appliances",
        "appliance_events",
        "agent_decisions",
        "energy_consumption",
        "tariff_history",
        "user_preferences",
        "feedback_events",
        "anomalies",
    } <= tables


def test_current_state_and_history_get_routes():
    assert client.get("/api/simulation/state").status_code == 200
    assert "sensors" in client.get("/api/sensors").json()
    assert "appliances" in client.get("/api/appliances").json()
    assert "current" in client.get("/api/energy").json()
    assert "tier" in client.get("/api/tariff").json()
    assert client.get("/api/agent/status").status_code == 200
    assert client.get("/api/agent/history").status_code == 200
    assert client.get("/api/anomalies").status_code == 200
    assert client.get("/api/preferences").status_code == 200


def test_simulation_controls_and_scenario():
    assert client.post("/api/simulation/start").status_code == 200
    assert client.post("/api/simulation/pause").status_code == 200
    assert client.post("/api/simulation/step", json={"dt_minutes": 2}).status_code == 200
    assert client.post("/api/simulation/reset").status_code == 200
    response = client.post(
        "/api/simulation/scenario",
        json={"scenario_id": "HIGH_ENERGY_LOAD"},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_appliance_action_and_invalid_action():
    response = client.post(
        "/api/appliances/tv_living_room/action",
        json={"action": "ON", "source": "USER"},
    )
    assert response.status_code == 200
    assert response.json()["state"]["appliances"]["tv_living_room"]["status"] == "ON"
    assert client.post(
        "/api/appliances/not-real/action",
        json={"action": "ON"},
    ).status_code == 404
    assert client.post(
        "/api/appliances/tv_living_room/action",
        json={"action": "UNSUPPORTED"},
    ).status_code == 400


def test_preferences_decisions_and_anomalies_persist():
    preference = client.post(
        "/api/preferences",
        json={
            "preferred_temperature": 21.5,
            "comfort_priority": 0.7,
            "energy_priority": 0.3,
            "selected_mode": "COMFORT",
        },
    )
    assert preference.status_code == 200
    assert client.get("/api/preferences").json()["selected_mode"] == "COMFORT"

    decision = client.post(
        "/api/agent/decisions",
        json={
            "decision": "recorded for future analysis",
            "reason": "supplied by caller",
            "confidence": 0.8,
            "expected_energy": 1.2,
            "sensor_snapshot": {"temperature": 24},
            "candidate_actions": [{"action": "OFF"}],
            "candidate_scores": {"OFF": 0.5},
        },
    )
    assert decision.status_code == 200
    assert client.get("/api/agent/history").json()["count"] >= 1

    anomaly = client.post(
        "/api/anomalies",
        json={
            "appliance_id": "washing_machine",
            "expected_power_watts": 800,
            "actual_power_watts": 1700,
            "severity": "HIGH",
        },
    )
    assert anomaly.status_code == 200
    assert anomaly.json()["deviation"] == 900
    assert client.get("/api/anomalies").json()["count"] >= 1


def test_home_websocket_sends_real_state_without_agent_loop():
    with client.websocket_connect("/ws/home") as websocket:
        connected = websocket.receive_json()
        assert connected["event"] == "connected"
        assert "rooms" in connected["state"]
        websocket.send_json({"action": "step", "dt_minutes": 1})
        update = websocket.receive_json()
        assert update["event"] == "state_update"
        assert "appliances" in update["state"]
        assert "total_load_watts" in update["state"]
