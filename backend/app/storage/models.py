"""Persisted order/package records (see README section on order storage).

Distinct from app.domain.package.Package: that model is the live, in-memory
package tracked by a running SortingLine while it's physically on the
conveyor. These models are the durable business record — which orders
exist, which packages belong to them, and their last known status — kept
in Postgres independent of whether a simulation is currently running.
"""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.package import PackageStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class OrderStatus(str, Enum):
    """Lifecycle of an order, independent of any individual package's
    status on the conveyor."""

    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class StationStatus(str, Enum):
    """Whether an order has been processed at a given station (see
    OrderStationStatusRecord, STATIONS)."""

    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    ERROR = "ERROR"


STATIONS: tuple[int, ...] = (1, 2, 3)
"""The fixed set of station ids every order is tracked against. A row is
seeded per station (PENDING) when an order is created (see
OrderRepository.create_order())."""


class OrderRecord(Base):
    """A customer order — one or more packages to be sorted."""

    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    destination_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[OrderStatus] = mapped_column(default=OrderStatus.CREATED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    packages: Mapped[list["PackageRecord"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    station_statuses: Mapped[list["OrderStationStatusRecord"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderStationStatusRecord.station_id"
    )
    barcodes: Mapped[list["OrderBarcodeRecord"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class PackageRecord(Base):
    """A persisted package record belonging to an order.

    package_id is expected to match the id a live app.domain.package.Package
    is assigned once it actually enters the sorting line (see
    SortingLine.create_package()), so a record here can be linked back to
    what happened to it physically — but nothing enforces that link
    automatically; this table is populated independently via /api/orders.
    """

    __tablename__ = "packages"

    package_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"))
    barcode: Mapped[str | None] = mapped_column(String(255), nullable=True)
    width: Mapped[float]
    length: Mapped[float]
    height: Mapped[float]
    weight: Mapped[float] = mapped_column(default=1.0)
    destination: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[PackageStatus] = mapped_column(default=PackageStatus.CREATED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    order: Mapped["OrderRecord"] = relationship(back_populates="packages")


class OrderStationStatusRecord(Base):
    """Whether one order has been processed at one station (see STATIONS).

    One row per (order_id, station_id), seeded PENDING for every station in
    STATIONS when the order is created (see OrderRepository.create_order())
    — never created ad hoc, so a lookup for a station_id outside STATIONS
    always misses (see OrderRepository.get_station_status()).
    """

    __tablename__ = "order_station_status"

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), primary_key=True)
    station_id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[StationStatus] = mapped_column(default=StationStatus.PENDING)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    order: Mapped["OrderRecord"] = relationship(back_populates="station_statuses")


class OrderBarcodeRecord(Base):
    """A barcode expected for an order, registered ahead of any physical
    package (see PackageRecord.barcode for the barcode actually read off a
    package that's been created).

    barcode is the primary key rather than a surrogate id, so a barcode
    maps to at most one order system-wide — registering it against a
    second order fails instead of silently shadowing the first (see
    OrderRepository.register_barcode()).
    """

    __tablename__ = "order_barcodes"

    barcode: Mapped[str] = mapped_column(String(255), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    order: Mapped["OrderRecord"] = relationship(back_populates="barcodes")
