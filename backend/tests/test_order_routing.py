import pytest
import pytest_asyncio

from app.storage.database import create_engine, create_session_factory, init_models
from app.storage.models import StationStatus
from app.storage.repository import OrderRepository
from app.storage.routing import make_order_gate_resolver


@pytest_asyncio.fixture
async def session_factory():
    engine = create_engine()
    await init_models(engine)
    factory = create_session_factory(engine)
    yield factory
    await engine.dispose()


async def _make_order_with_barcode(session_factory, barcode: str) -> str:
    async with session_factory() as session:
        repo = OrderRepository(session)
        order = await repo.create_order(f"ORD-{barcode}", None, None)
        await repo.register_barcode(order.order_id, barcode)
        return order.order_id


async def _process_station(session_factory, order_id: str, station_id: int) -> None:
    async with session_factory() as session:
        repo = OrderRepository(session)
        await repo.update_station_status(order_id, station_id, StationStatus.PROCESSED)


@pytest.mark.asyncio
async def test_resolve_barcode_not_registered_to_any_order(session_factory):
    resolve = make_order_gate_resolver(session_factory)
    resolution = await resolve("does-not-exist")
    assert resolution.order_found is False


@pytest.mark.asyncio
async def test_resolve_order_with_no_stations_processed_routes_to_gate_1(session_factory):
    await _make_order_with_barcode(session_factory, "BC-NONE")
    resolve = make_order_gate_resolver(session_factory)
    resolution = await resolve("BC-NONE")
    assert resolution.order_found is True
    assert resolution.gate_id == 1


@pytest.mark.asyncio
async def test_resolve_order_with_station_1_processed_routes_to_gate_2(session_factory):
    order_id = await _make_order_with_barcode(session_factory, "BC-S1")
    await _process_station(session_factory, order_id, 1)
    resolve = make_order_gate_resolver(session_factory)
    resolution = await resolve("BC-S1")
    assert resolution.gate_id == 2


@pytest.mark.asyncio
async def test_resolve_order_with_stations_1_and_2_processed_routes_to_gate_3(session_factory):
    order_id = await _make_order_with_barcode(session_factory, "BC-S12")
    await _process_station(session_factory, order_id, 1)
    await _process_station(session_factory, order_id, 2)
    resolve = make_order_gate_resolver(session_factory)
    resolution = await resolve("BC-S12")
    assert resolution.gate_id == 3


@pytest.mark.asyncio
async def test_resolve_order_with_every_station_processed_has_no_gate(session_factory):
    order_id = await _make_order_with_barcode(session_factory, "BC-S123")
    await _process_station(session_factory, order_id, 1)
    await _process_station(session_factory, order_id, 2)
    await _process_station(session_factory, order_id, 3)
    resolve = make_order_gate_resolver(session_factory)
    resolution = await resolve("BC-S123")
    assert resolution.order_found is True
    assert resolution.gate_id is None
