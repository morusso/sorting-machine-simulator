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
    assert body["package_id"] == "PKG-000001"
    assert body["barcode"] is None
    assert body["destination"] is None
    assert body["status"] == "IN_TRANSIT"


def test_create_package_defaults_to_a_1kg_weight(client):
    response = client.post("/api/packages", json={"barcode": "5901234567890"})
    assert response.json()["weight"] == 1.0


def test_create_package_accepts_a_custom_weight(client):
    response = client.post("/api/packages", json={"barcode": "5901234567890", "weight": 4.2})
    assert response.json()["weight"] == 4.2


def test_create_package_assigns_sequential_ids(client):
    first = client.post("/api/packages", json={"barcode": "5901234567890"}).json()
    second = client.post("/api/packages", json={"barcode": "5901234567890"}).json()
    assert first["package_id"] == "PKG-000001"
    assert second["package_id"] == "PKG-000002"


def test_create_package_without_barcode_returns_unprocessable(client):
    response = client.post("/api/packages", json={})
    assert response.status_code == 422


def test_simulation_status_starts_stopped(client):
    response = client.get("/api/simulation/status")
    assert response.status_code == 200
    assert response.json() == {"state": "STOPPED", "time": 0.0, "emergency_stopped": False}


def test_simulation_status_reflects_running_after_start(client):
    client.post("/api/simulation/start")
    response = client.get("/api/simulation/status")
    assert response.json()["state"] == "RUNNING"


def test_start_stop_reset_lifecycle(client):
    assert client.post("/api/simulation/start").json()["state"] == "RUNNING"
    assert client.post("/api/simulation/stop").json()["state"] == "STOPPED"
    assert client.post("/api/simulation/reset").json() == {"state": "STOPPED", "time": 0.0, "emergency_stopped": False}


def test_start_twice_returns_conflict(client):
    assert client.post("/api/simulation/start").status_code == 200
    response = client.post("/api/simulation/start")
    assert response.status_code == 409


def test_stop_without_starting_returns_conflict(client):
    response = client.post("/api/simulation/stop")
    assert response.status_code == 409


def test_reset_while_running_stops_and_zeroes_time(client):
    client.post("/api/simulation/start")
    response = client.post("/api/simulation/reset")
    assert response.json() == {"state": "STOPPED", "time": 0.0, "emergency_stopped": False}


def test_reset_clears_packages(client):
    client.post("/api/packages", json={"barcode": "5901234567890"})
    client.post("/api/simulation/reset")
    response = client.get("/api/statistics")
    assert response.json()["total_packages"] == 0


def test_emergency_stop_sets_flag_and_stops_the_engine(client):
    client.post("/api/simulation/start")
    response = client.post("/api/simulation/emergency_stop")
    assert response.status_code == 200
    body = response.json()
    assert body["emergency_stopped"] is True
    assert body["state"] == "STOPPED"


def test_emergency_stop_reflected_in_status(client):
    client.post("/api/simulation/emergency_stop")
    response = client.get("/api/simulation/status")
    assert response.json()["emergency_stopped"] is True


def test_start_after_emergency_stop_returns_conflict(client):
    client.post("/api/simulation/emergency_stop")
    response = client.post("/api/simulation/start")
    assert response.status_code == 409


def test_reset_after_emergency_stop_allows_start_again(client):
    client.post("/api/simulation/emergency_stop")
    client.post("/api/simulation/reset")
    response = client.post("/api/simulation/start")
    assert response.status_code == 200
    assert response.json()["emergency_stopped"] is False


def test_emergency_stop_from_stopped_succeeds(client):
    response = client.post("/api/simulation/emergency_stop")
    assert response.status_code == 200
    assert response.json()["emergency_stopped"] is True


def test_set_conveyor_speed(client):
    response = client.post("/api/conveyor/speed", json={"speed": 1.5})
    assert response.status_code == 200
    body = response.json()
    assert body["target_speed"] == 1.5
    assert body["speed"] == 1.0  # ramps gradually; unchanged until the engine ticks


def test_set_conveyor_speed_above_max_returns_bad_request(client):
    response = client.post("/api/conveyor/speed", json={"speed": 99.0})
    assert response.status_code == 400


def test_set_conveyor_speed_negative_returns_bad_request(client):
    response = client.post("/api/conveyor/speed", json={"speed": -1.0})
    assert response.status_code == 400


def test_set_conveyor_speed_without_speed_returns_unprocessable(client):
    response = client.post("/api/conveyor/speed", json={})
    assert response.status_code == 422


def test_set_simulation_speed_updates_multiplier(client):
    response = client.post("/api/simulation/speed", json={"speed_multiplier": 10.0})
    assert response.status_code == 200
    body = response.json()
    assert body["speed_multiplier"] == 10.0


def test_set_simulation_speed_non_positive_returns_bad_request(client):
    response = client.post("/api/simulation/speed", json={"speed_multiplier": 0.0})
    assert response.status_code == 400


def test_set_simulation_speed_without_multiplier_returns_unprocessable(client):
    response = client.post("/api/simulation/speed", json={})
    assert response.status_code == 422


def test_get_statistics_starts_empty(client):
    response = client.get("/api/statistics")
    assert response.status_code == 200
    body = response.json()
    assert body["total_packages"] == 0
    assert body["success_rate"] is None


def test_get_statistics_counts_every_created_package(client):
    for _ in range(3):
        client.post("/api/packages", json={"barcode": "5901234567890"})
    response = client.get("/api/statistics")
    assert response.json()["total_packages"] == 3


def test_websocket_streams_simulation_state(client):
    with client.websocket_connect("/ws") as websocket:
        message = websocket.receive_json()
    assert message["type"] == "simulation_state"
    assert message["engine_state"] == "STOPPED"
    assert "conveyor" in message
    assert "packages" in message
    assert "gates" in message
    assert len(message["gates"]) == 3
    assert "statistics" in message
    assert message["gravity_segment"]["packages"] == []
    assert message["gravity_segment"]["length"] > 0


def test_websocket_reflects_a_package_created_beforehand(client):
    client.post("/api/packages", json={"barcode": "5901234567890"})
    with client.websocket_connect("/ws") as websocket:
        message = websocket.receive_json()
    assert len(message["packages"]) == 1
    assert message["packages"][0]["id"] == "PKG-000001"
    assert message["statistics"]["total_packages"] == 1


def test_websocket_broadcasts_to_multiple_connected_clients(client):
    with client.websocket_connect("/ws") as first, client.websocket_connect("/ws") as second:
        first_message = first.receive_json()
        second_message = second.receive_json()
    assert first_message["type"] == "simulation_state"
    assert second_message["type"] == "simulation_state"


def test_websocket_survives_a_client_disconnecting(client):
    with client.websocket_connect("/ws") as first:
        first.receive_json()
    # `first` is now disconnected; the server must not crash broadcasting
    # to it on the next tick, and must still serve new connections/requests.
    with client.websocket_connect("/ws") as second:
        message = second.receive_json()
    assert message["type"] == "simulation_state"
    assert client.get("/api/simulation/status").status_code == 200


def test_engine_start_is_reflected_in_the_next_broadcast(client):
    with client.websocket_connect("/ws") as websocket:
        assert websocket.receive_json()["engine_state"] == "STOPPED"
        client.post("/api/simulation/start")
        assert websocket.receive_json()["engine_state"] == "RUNNING"


def test_running_simulation_advances_package_position_over_broadcasts(client):
    client.post("/api/packages", json={"barcode": "5901234567890"})
    client.post("/api/simulation/start")
    with client.websocket_connect("/ws") as websocket:
        first = websocket.receive_json()
        second = websocket.receive_json()
    assert second["timestamp"] > first["timestamp"]
    assert second["packages"][0]["position"] > first["packages"][0]["position"]


def test_cors_header_present_for_allowed_origin(client):
    response = client.get("/api/simulation/status", headers={"Origin": "http://localhost:3000"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_header_absent_for_disallowed_origin(client):
    response = client.get("/api/simulation/status", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in response.headers
