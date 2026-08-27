from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.api.state import SimulationState
from app.domain.package import Package
from app.simulation.engine import EngineState

router = APIRouter()


class CreatePackageRequest(BaseModel):
    """Request body for POST /api/packages (see README section 30)."""

    barcode: str


class SetConveyorSpeedRequest(BaseModel):
    """Request body for POST /api/conveyor/speed (see README section 30)."""

    speed: float


class SimulationStatusResponse(BaseModel):
    """Response body for GET /api/simulation/status."""

    state: EngineState
    time: float


class ConveyorStatusResponse(BaseModel):
    """Response body for POST /api/conveyor/speed."""

    speed: float
    target_speed: float


def _state(request: Request) -> SimulationState:
    """Fetch the shared SimulationState stashed on the app by main.py."""
    return request.app.state.simulation


@router.post("/api/packages", response_model=Package)
async def create_package(body: CreatePackageRequest, request: Request) -> Package:
    """Create a package with the given barcode and place it on the conveyor."""
    return await _state(request).create_package(body.barcode)


@router.get("/api/simulation/status", response_model=SimulationStatusResponse)
async def get_status(request: Request) -> SimulationStatusResponse:
    """Return the engine's current lifecycle state and simulated time."""
    state = _state(request)
    return SimulationStatusResponse(state=state.engine.state, time=state.clock.now())


@router.post("/api/simulation/start", response_model=SimulationStatusResponse)
async def start_simulation(request: Request) -> SimulationStatusResponse:
    """Start the simulation (see SimulationEngine.start())."""
    state = _state(request)
    try:
        state.engine.start()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return SimulationStatusResponse(state=state.engine.state, time=state.clock.now())


@router.post("/api/simulation/stop", response_model=SimulationStatusResponse)
async def stop_simulation(request: Request) -> SimulationStatusResponse:
    """Stop the simulation (see SimulationEngine.stop())."""
    state = _state(request)
    try:
        state.engine.stop()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return SimulationStatusResponse(state=state.engine.state, time=state.clock.now())


@router.post("/api/simulation/reset", response_model=SimulationStatusResponse)
async def reset_simulation(request: Request) -> SimulationStatusResponse:
    """Reset the simulation to a fresh, empty state (see SimulationState.reset())."""
    state = _state(request)
    state.reset()
    return SimulationStatusResponse(state=state.engine.state, time=state.clock.now())


@router.post("/api/conveyor/speed", response_model=ConveyorStatusResponse)
async def set_conveyor_speed(body: SetConveyorSpeedRequest, request: Request) -> ConveyorStatusResponse:
    """Command a new target speed for the conveyor (see DrivenConveyorSegment.set_speed())."""
    state = _state(request)
    try:
        state.segment.set_speed(body.speed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ConveyorStatusResponse(speed=state.segment.speed, target_speed=state.segment.target_speed)
