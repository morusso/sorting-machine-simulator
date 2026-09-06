"""Resolves which gate a scanned barcode should route to from the order
storage service, bridging the live simulation
(app.simulation.sorting_line.SortingLine) to persisted order/station data
without either depending on the other's internals: SortingLine only ever
sees an OrderGateResolver (an async barcode -> OrderGateResolution
function) and app.controllers.controller.GateOverride, never SQLAlchemy or
this module's models directly.

Routing rule (see README section on order/station-driven routing): gate 1
is for orders whose stations are all still PENDING, gate 2 once station 1
has been PROCESSED, gate 3 once stations 1 and 2 have both been PROCESSED,
and no gate at all (forced REJECTED) once every station in STATIONS has
been PROCESSED — there's nothing further to sort it into. A barcode with
no matching order at all is left alone (order_found=False) so the caller
falls back to its own default (see Controller.handle_scan_result's
routing_table).
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.storage.models import StationStatus
from app.storage.repository import BarcodeNotFoundError, OrderRepository

# Gate to open for a given count of PROCESSED stations on the barcode's
# order. A count equal to len(STATIONS) (every station processed) has
# deliberately no entry here — see OrderGateResolution.gate_id.
_GATE_BY_PROCESSED_COUNT: dict[int, int] = {0: 1, 1: 2, 2: 3}


@dataclass(frozen=True)
class OrderGateResolution:
    """Result of resolving a barcode against the order storage service.

    Attributes:
        order_found: Whether the barcode is registered to any order. False
            means gate_id is meaningless — the caller should fall back to
            its own default routing instead of treating this as "no gate".
        gate_id: Gate to route to, or None if every station on the order
            has been processed (no gate opens). Only meaningful when
            order_found is True.
    """

    order_found: bool
    gate_id: int | None = None


OrderGateResolver = Callable[[str], Awaitable[OrderGateResolution]]


def make_order_gate_resolver(session_factory: async_sessionmaker[AsyncSession]) -> OrderGateResolver:
    """Build an OrderGateResolver backed by a real database session per call.

    Args:
        session_factory: Opens one session per resolve() call (see
            app.storage.database.create_session_factory) — resolution
            happens on the simulation's own tick loop, not inside a
            request, so it can't reuse a request-scoped session.

    Returns:
        An OrderGateResolver.
    """

    async def resolve(barcode: str) -> OrderGateResolution:
        async with session_factory() as session:
            repo = OrderRepository(session)
            try:
                order = await repo.get_order_by_barcode(barcode)
            except BarcodeNotFoundError:
                return OrderGateResolution(order_found=False)
            processed_count = sum(1 for station in order.station_statuses if station.status == StationStatus.PROCESSED)
            return OrderGateResolution(order_found=True, gate_id=_GATE_BY_PROCESSED_COUNT.get(processed_count))

    return resolve
