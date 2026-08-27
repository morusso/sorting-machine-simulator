import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_create_package_starts_in_transit_and_unscanned(client):
    response = client.post("/api/packages", json={"barcode": "5901234567890"})
    assert response.status_code == 200
    body = response.json()
    assert body["barcode"] is None
    assert body["destination"] is None
    assert body["status"] == "IN_TRANSIT"


def test_simulation_status_starts_stopped(client):
    response = client.get("/api/simulation/status")
    assert response.status_code == 200
    assert response.json() == {"state": "STOPPED", "time": 0.0}


def test_start_stop_reset_lifecycle(client):
    assert client.post("/api/simulation/start").json()["state"] == "RUNNING"
    assert client.post("/api/simulation/stop").json()["state"] == "STOPPED"
    assert client.post("/api/simulation/reset").json() == {"state": "STOPPED", "time": 0.0}


def test_start_twice_returns_conflict(client):
    assert client.post("/api/simulation/start").status_code == 200
    response = client.post("/api/simulation/start")
    assert response.status_code == 409


def test_set_conveyor_speed(client):
    response = client.post("/api/conveyor/speed", json={"speed": 1.5})
    assert response.status_code == 200
    body = response.json()
    assert body["target_speed"] == 1.5
    assert body["speed"] == 1.0  # ramps gradually; unchanged until the engine ticks


def test_set_conveyor_speed_above_max_returns_bad_request(client):
    response = client.post("/api/conveyor/speed", json={"speed": 99.0})
    assert response.status_code == 400


def test_reset_clears_packages(client):
    client.post("/api/packages", json={"barcode": "5901234567890"})
    client.post("/api/simulation/reset")
    response = client.get("/api/simulation/status")
    assert response.json()["time"] == 0.0


def test_websocket_streams_simulation_state(client):
    with client.websocket_connect("/ws") as websocket:
        message = websocket.receive_json()
    assert message["type"] == "simulation_state"
    assert "conveyor" in message
    assert "packages" in message
    assert "gates" in message
    assert len(message["gates"]) == 3
    assert "statistics" in message


def test_get_statistics_starts_empty(client):
    response = client.get("/api/statistics")
    assert response.status_code == 200
    body = response.json()
    assert body["total_packages"] == 0
    assert body["success_rate"] is None


def test_get_statistics_counts_created_package(client):
    client.post("/api/packages", json={"barcode": "5901234567890"})
    response = client.get("/api/statistics")
    assert response.json()["total_packages"] == 1
