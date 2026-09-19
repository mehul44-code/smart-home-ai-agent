import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"


def test_status_endpoint():
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert "indoor_temp_c" in data
    assert "tariff" in data


def test_appliances_endpoint():
    response = client.get("/api/appliances")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] > 0
    assert "ac_living_room" in data["appliances"]


def test_agent_step_endpoint():
    response = client.post("/api/agent/step")
    assert response.status_code == 200
    data = response.json()
    assert "stage_1_perception" in data
    assert "stage_7_explanation" in data
