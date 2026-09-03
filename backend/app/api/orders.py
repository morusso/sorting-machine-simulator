"""REST API for the persisted order/package storage service (see app.storage).

Independent of the live SortingLine simulation exposed by app.api.routes:
this is the durable record of what orders and packages exist, kept in
Postgres, not the in-memory physical state of packages currently on a
conveyor.
"""

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.package import PackageStatus
from app.storage.database import get_session
from app.storage.models import OrderStatus, StationStatus
from app.storage.models import PackageRecord as PackageRecordModel
from app.storage.repository import OrderNotFoundError, OrderRepository, PackageNotFoundError, StationNotFoundError

router = APIRouter()


class CreateOrderRequest(BaseModel):
    customer_name: str | None = None
    destination_address: str | None = None


class UpdateOrderStatusRequest(BaseModel):
    status: OrderStatus


class UpdateStationStatusRequest(BaseModel):
    status: StationStatus


class CreateOrderPackageRequest(BaseModel):
    """Request body for POST /api/orders/{order_id}/packages.

    package_id should match the id assigned once the package actually
    enters the sorting line (see SortingLine.create_package(), format
    "PKG-000123"), to link this record back to what happened to it
    physically. Left unset, a placeholder id is generated instead for
    orders tracked before the package is ever created on the line.
    """

    package_id: str | None = None
    barcode: str | None = None
    width: float
    length: float
    height: float
    weight: float = 1.0
    destination: int | None = None
    status: PackageStatus = PackageStatus.CREATED


class OrderPackageResponse(BaseModel):
    package_id: str
    order_id: str
    barcode: str | None
    width: float
    length: float
    height: float
    weight: float
    destination: int | None
    status: PackageStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StationStatusResponse(BaseModel):
    station_id: int
    status: StationStatus
    processed_at: datetime | None

    model_config = {"from_attributes": True}


class OrderResponse(BaseModel):
    order_id: str
    customer_name: str | None
    destination_address: str | None
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    packages: list[OrderPackageResponse]
    station_statuses: list[StationStatusResponse]

    model_config = {"from_attributes": True}


@router.post("/api/orders", response_model=OrderResponse)
async def create_order(body: CreateOrderRequest, session: AsyncSession = Depends(get_session)) -> OrderResponse:
    """Create a new order."""
    repo = OrderRepository(session)
    order = await repo.create_order(f"ORD-{uuid4().hex[:12]}", body.customer_name, body.destination_address)
    return OrderResponse.model_validate(order)


@router.get("/api/orders", response_model=list[OrderResponse])
async def list_orders(session: AsyncSession = Depends(get_session)) -> list[OrderResponse]:
    """List every order, each with its packages."""
    repo = OrderRepository(session)
    orders = await repo.list_orders()
    return [OrderResponse.model_validate(order) for order in orders]


@router.get("/api/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, session: AsyncSession = Depends(get_session)) -> OrderResponse:
    """Fetch one order, with its packages."""
    repo = OrderRepository(session)
    try:
        order = await repo.get_order(order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"order {order_id!r} not found") from exc
    return OrderResponse.model_validate(order)


@router.patch("/api/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: str, body: UpdateOrderStatusRequest, session: AsyncSession = Depends(get_session)
) -> OrderResponse:
    """Update an order's status (e.g. mark it IN_PROGRESS/COMPLETED/CANCELLED)."""
    repo = OrderRepository(session)
    try:
        order = await repo.update_order_status(order_id, body.status)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"order {order_id!r} not found") from exc
    return OrderResponse.model_validate(order)


@router.delete("/api/orders/{order_id}", status_code=204)
async def delete_order(order_id: str, session: AsyncSession = Depends(get_session)) -> Response:
    """Delete an order and every package record belonging to it."""
    repo = OrderRepository(session)
    try:
        await repo.delete_order(order_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"order {order_id!r} not found") from exc
    return Response(status_code=204)


@router.post("/api/orders/{order_id}/packages", response_model=OrderPackageResponse)
async def add_order_package(
    order_id: str, body: CreateOrderPackageRequest, session: AsyncSession = Depends(get_session)
) -> OrderPackageResponse:
    """Attach a package record to an order."""
    repo = OrderRepository(session)
    package = PackageRecordModel(
        package_id=body.package_id or f"PKG-{uuid4().hex[:12]}",
        barcode=body.barcode,
        width=body.width,
        length=body.length,
        height=body.height,
        weight=body.weight,
        destination=body.destination,
        status=body.status,
    )
    try:
        package = await repo.add_package(order_id, package)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"order {order_id!r} not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return OrderPackageResponse.model_validate(package)


@router.get("/api/orders/{order_id}/packages/{package_id}", response_model=OrderPackageResponse)
async def get_order_package(
    order_id: str, package_id: str, session: AsyncSession = Depends(get_session)
) -> OrderPackageResponse:
    """Fetch one package record belonging to an order."""
    repo = OrderRepository(session)
    try:
        package = await repo.get_package(order_id, package_id)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"order {order_id!r} not found") from exc
    except PackageNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"package {package_id!r} not found in order {order_id!r}") from exc
    return OrderPackageResponse.model_validate(package)


@router.patch("/api/orders/{order_id}/stations/{station_id}", response_model=StationStatusResponse)
async def update_station_status(
    order_id: str, station_id: int, body: UpdateStationStatusRequest, session: AsyncSession = Depends(get_session)
) -> StationStatusResponse:
    """Mark whether an order has been processed at one station (see app.storage.models.STATIONS).

    processed_at is stamped the moment status stops being PENDING, and
    cleared again if it's ever reset back to PENDING.
    """
    repo = OrderRepository(session)
    try:
        station = await repo.update_station_status(order_id, station_id, body.status)
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"order {order_id!r} not found") from exc
    except StationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"station {station_id} not found in order {order_id!r}") from exc
    return StationStatusResponse.model_validate(station)
