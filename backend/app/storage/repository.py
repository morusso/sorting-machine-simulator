"""Async CRUD access to persisted orders/packages (see app.storage.models)."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.storage.models import STATIONS, OrderRecord, OrderStationStatusRecord, OrderStatus, PackageRecord, StationStatus

_EAGER_LOAD = [selectinload(OrderRecord.packages), selectinload(OrderRecord.station_statuses)]


class OrderNotFoundError(Exception):
    """Raised when an order_id has no matching OrderRecord."""


class PackageNotFoundError(Exception):
    """Raised when a package_id has no matching PackageRecord in the given order."""


class StationNotFoundError(Exception):
    """Raised when a station_id isn't in STATIONS (so no row was seeded for it)."""


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_order(self, order_id: str, customer_name: str | None, destination_address: str | None) -> OrderRecord:
        order = OrderRecord(order_id=order_id, customer_name=customer_name, destination_address=destination_address)
        self.session.add(order)
        for station_id in STATIONS:
            self.session.add(OrderStationStatusRecord(order_id=order_id, station_id=station_id))
        await self.session.commit()
        return await self.get_order(order_id)

    async def get_order(self, order_id: str) -> OrderRecord:
        # populate_existing is required so the eager-load option actually
        # takes effect when order_id is already in the session's identity
        # map (e.g. right after create_order's insert) — session.get()
        # otherwise returns the cached object as-is, options and all.
        order = await self.session.get(OrderRecord, order_id, options=_EAGER_LOAD, populate_existing=True)
        if order is None:
            raise OrderNotFoundError(order_id)
        return order

    async def list_orders(self) -> list[OrderRecord]:
        result = await self.session.execute(select(OrderRecord).options(*_EAGER_LOAD))
        return list(result.scalars().all())

    async def update_order_status(self, order_id: str, status: OrderStatus) -> OrderRecord:
        order = await self.get_order(order_id)
        order.status = status
        await self.session.commit()
        return await self.get_order(order_id)

    async def delete_order(self, order_id: str) -> None:
        order = await self.get_order(order_id)
        await self.session.delete(order)
        await self.session.commit()

    async def add_package(self, order_id: str, package: PackageRecord) -> PackageRecord:
        await self.get_order(order_id)
        package.order_id = order_id
        self.session.add(package)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ValueError(f"package_id {package.package_id!r} already exists") from exc
        await self.session.refresh(package)
        return package

    async def get_package(self, order_id: str, package_id: str) -> PackageRecord:
        order = await self.get_order(order_id)
        for package in order.packages:
            if package.package_id == package_id:
                return package
        raise PackageNotFoundError(package_id)

    async def get_station_status(self, order_id: str, station_id: int) -> OrderStationStatusRecord:
        order = await self.get_order(order_id)
        for station in order.station_statuses:
            if station.station_id == station_id:
                return station
        raise StationNotFoundError(station_id)

    async def update_station_status(self, order_id: str, station_id: int, status: StationStatus) -> OrderStationStatusRecord:
        """Set one station's status, stamping processed_at when it's no
        longer PENDING (see OrderStationStatusRecord) — cleared again if
        it's ever reset back to PENDING."""
        station = await self.get_station_status(order_id, station_id)
        station.status = status
        station.processed_at = None if status == StationStatus.PENDING else datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(station)
        return station
