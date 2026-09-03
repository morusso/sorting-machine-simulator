import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    # The session-wide Postgres container (see conftest.py) is shared
    # across every test, so previously created orders/packages would
    # otherwise leak between tests — clear them out before each one.
    with TestClient(app) as test_client:
        for order in test_client.get("/api/orders").json():
            test_client.delete(f"/api/orders/{order['order_id']}")
        yield test_client


def test_create_order_defaults_to_created_status_and_no_packages(client):
    response = client.post("/api/orders", json={"customer_name": "Acme", "destination_address": "Warsaw"})
    assert response.status_code == 200
    body = response.json()
    assert body["order_id"].startswith("ORD-")
    assert body["customer_name"] == "Acme"
    assert body["destination_address"] == "Warsaw"
    assert body["status"] == "CREATED"
    assert body["packages"] == []


def test_create_order_seeds_pending_status_for_every_station(client):
    order = client.post("/api/orders", json={}).json()
    stations = order["station_statuses"]
    assert [s["station_id"] for s in stations] == [1, 2, 3]
    assert all(s["status"] == "PENDING" and s["processed_at"] is None for s in stations)


def test_update_station_status_marks_it_processed_with_a_timestamp(client):
    order = client.post("/api/orders", json={}).json()
    response = client.patch(f"/api/orders/{order['order_id']}/stations/2", json={"status": "PROCESSED"})
    assert response.status_code == 200
    body = response.json()
    assert body["station_id"] == 2
    assert body["status"] == "PROCESSED"
    assert body["processed_at"] is not None

    reloaded = client.get(f"/api/orders/{order['order_id']}").json()
    by_station = {s["station_id"]: s for s in reloaded["station_statuses"]}
    assert by_station[2]["status"] == "PROCESSED"
    assert by_station[1]["status"] == "PENDING"
    assert by_station[3]["status"] == "PENDING"


def test_update_station_status_back_to_pending_clears_processed_at(client):
    order = client.post("/api/orders", json={}).json()
    client.patch(f"/api/orders/{order['order_id']}/stations/1", json={"status": "PROCESSED"})
    response = client.patch(f"/api/orders/{order['order_id']}/stations/1", json={"status": "PENDING"})
    assert response.json()["processed_at"] is None


def test_update_station_status_returns_404_for_unknown_station(client):
    order = client.post("/api/orders", json={}).json()
    response = client.patch(f"/api/orders/{order['order_id']}/stations/99", json={"status": "PROCESSED"})
    assert response.status_code == 404


def test_update_station_status_returns_404_for_missing_order(client):
    response = client.patch("/api/orders/does-not-exist/stations/1", json={"status": "PROCESSED"})
    assert response.status_code == 404


def test_create_order_without_body_fields_is_allowed(client):
    response = client.post("/api/orders", json={})
    assert response.status_code == 200
    assert response.json()["customer_name"] is None


def test_get_order_returns_404_when_missing(client):
    response = client.get("/api/orders/does-not-exist")
    assert response.status_code == 404


def test_list_orders_returns_every_created_order(client):
    client.post("/api/orders", json={})
    client.post("/api/orders", json={})
    response = client.get("/api/orders")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_order_status(client):
    order = client.post("/api/orders", json={}).json()
    response = client.patch(f"/api/orders/{order['order_id']}/status", json={"status": "COMPLETED"})
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"


def test_update_order_status_returns_404_when_missing(client):
    response = client.patch("/api/orders/does-not-exist/status", json={"status": "COMPLETED"})
    assert response.status_code == 404


def test_delete_order_removes_it(client):
    order = client.post("/api/orders", json={}).json()
    response = client.delete(f"/api/orders/{order['order_id']}")
    assert response.status_code == 204
    assert client.get(f"/api/orders/{order['order_id']}").status_code == 404


def test_delete_order_returns_404_when_missing(client):
    response = client.delete("/api/orders/does-not-exist")
    assert response.status_code == 404


def test_add_package_to_order(client):
    order = client.post("/api/orders", json={}).json()
    response = client.post(
        f"/api/orders/{order['order_id']}/packages",
        json={"barcode": "5901234567890", "width": 0.25, "length": 0.4, "height": 0.2},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["order_id"] == order["order_id"]
    assert body["barcode"] == "5901234567890"
    assert body["status"] == "CREATED"


def test_add_package_accepts_a_caller_supplied_id(client):
    order = client.post("/api/orders", json={}).json()
    response = client.post(
        f"/api/orders/{order['order_id']}/packages",
        json={"package_id": "PKG-000001", "width": 0.25, "length": 0.4, "height": 0.2},
    )
    assert response.json()["package_id"] == "PKG-000001"


def test_add_package_rejects_a_duplicate_id(client):
    order = client.post("/api/orders", json={}).json()
    body = {"package_id": "PKG-000001", "width": 0.25, "length": 0.4, "height": 0.2}
    client.post(f"/api/orders/{order['order_id']}/packages", json=body)
    response = client.post(f"/api/orders/{order['order_id']}/packages", json=body)
    assert response.status_code == 409


def test_add_package_to_missing_order_returns_404(client):
    response = client.post(
        "/api/orders/does-not-exist/packages", json={"width": 0.25, "length": 0.4, "height": 0.2}
    )
    assert response.status_code == 404


def test_get_order_includes_its_packages(client):
    order = client.post("/api/orders", json={}).json()
    client.post(f"/api/orders/{order['order_id']}/packages", json={"width": 0.25, "length": 0.4, "height": 0.2})
    response = client.get(f"/api/orders/{order['order_id']}")
    assert len(response.json()["packages"]) == 1


def test_get_order_package(client):
    order = client.post("/api/orders", json={}).json()
    package = client.post(
        f"/api/orders/{order['order_id']}/packages", json={"width": 0.25, "length": 0.4, "height": 0.2}
    ).json()
    response = client.get(f"/api/orders/{order['order_id']}/packages/{package['package_id']}")
    assert response.status_code == 200
    assert response.json()["package_id"] == package["package_id"]


def test_get_order_package_returns_404_when_missing(client):
    order = client.post("/api/orders", json={}).json()
    response = client.get(f"/api/orders/{order['order_id']}/packages/PKG-999999")
    assert response.status_code == 404
