from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.domain.package import Package
from app.simulation.engine import EngineState
from app.simulation.sorting_line import SortingLine

router = APIRouter()


class CreatePackageRequest(BaseModel):
    """Request body for POST /api/packages (see README section 30).

    weight only matters once the package reaches the gravity buffer
    segment past the driven segment's end (see README section 4.1a).
    """

    barcode: str
    weight: float = 1.0


class SetConveyorSpeedRequest(BaseModel):
    """Request body for POST /api/conveyor/speed (see README section 30)."""

    speed: float


class SetSimulationSpeedRequest(BaseModel):
    """Request body for POST /api/simulation/speed (see README section 20-21).

    Not restricted to the x1/x2/x10/x100 presets from the README's
    example — any positive multiplier is accepted (see
    SimulationEngine.set_speed_multiplier()).
    """

    speed_multiplier: float


class SimulationStatusResponse(BaseModel):
    """Response body for GET /api/simulation/status and every simulation
    lifecycle command (start/pause/resume/stop/reset/emergency_stop)."""

    state: EngineState
    time: float
    emergency_stopped: bool


class ConveyorStatusResponse(BaseModel):
    """Response body for POST /api/conveyor/speed."""

    speed: float
    target_speed: float


class SimulationSpeedResponse(BaseModel):
    """Response body for POST /api/simulation/speed."""

    speed_multiplier: float


class StatisticsResponse(BaseModel):
    """Response body for GET /api/statistics (see README section 34)."""

    total_packages: int
    sorted_packages: int
    rejected_packages: int
    unknown_codes: int
    scan_errors: int
    gate_errors: int
    error_packages: int
    average_scan_time: float | None
    average_sort_time: float | None
    throughput: float
    packages_per_second: float
    success_rate: float | None


def _state(request: Request) -> SortingLine:
    """Fetch the shared SortingLine stashed on the app by main.py."""
    return request.app.state.simulation


def _status_response(state: SortingLine) -> SimulationStatusResponse:
    """Build a SimulationStatusResponse reflecting state's current lifecycle."""
    return SimulationStatusResponse(
        state=state.engine.state, time=state.clock.now(), emergency_stopped=state.emergency_stopped
    )


@router.post("/api/packages", response_model=Package)
async def create_package(body: CreatePackageRequest, request: Request) -> Package:
    """Create a package with the given barcode and place it on the conveyor."""
    return await _state(request).create_package(body.barcode, weight=body.weight)


@router.get("/api/simulation/status", response_model=SimulationStatusResponse)
async def get_status(request: Request) -> SimulationStatusResponse:
    """Return the engine's current lifecycle state and simulated time."""
    return _status_response(_state(request))


@router.post("/api/simulation/start", response_model=SimulationStatusResponse)
async def start_simulation(request: Request) -> SimulationStatusResponse:
    """Start the simulation (see SimulationEngine.start())."""
    state = _state(request)
    if state.emergency_stopped:
        raise HTTPException(status_code=409, detail="cannot start: emergency stop is active, reset first")
    try:
        state.engine.start()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _status_response(state)


@router.post("/api/simulation/pause", response_model=SimulationStatusResponse)
async def pause_simulation(request: Request) -> SimulationStatusResponse:
    """Pause the simulation, freezing the clock (see SimulationEngine.pause())."""
    state = _state(request)
    try:
        state.engine.pause()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _status_response(state)


@router.post("/api/simulation/resume", response_model=SimulationStatusResponse)
async def resume_simulation(request: Request) -> SimulationStatusResponse:
    """Resume a paused simulation (see SimulationEngine.resume())."""
    state = _state(request)
    try:
        state.engine.resume()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _status_response(state)


@router.post("/api/simulation/stop", response_model=SimulationStatusResponse)
async def stop_simulation(request: Request) -> SimulationStatusResponse:
    """Stop the simulation (see SimulationEngine.stop())."""
    state = _state(request)
    try:
        state.engine.stop()
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _status_response(state)


@router.post("/api/simulation/reset", response_model=SimulationStatusResponse)
async def reset_simulation(request: Request) -> SimulationStatusResponse:
    """Reset the simulation to a fresh, empty state (see SortingLine.reset())."""
    state = _state(request)
    state.reset()
    return _status_response(state)


@router.post("/api/simulation/emergency_stop", response_model=SimulationStatusResponse)
async def emergency_stop(request: Request) -> SimulationStatusResponse:
    """Trip the emergency stop (see SortingLine.emergency_stop(), README section 26).

    Always succeeds. Recovery requires POST /api/simulation/reset.
    """
    state = _state(request)
    await state.emergency_stop()
    return _status_response(state)


@router.post("/api/simulation/speed", response_model=SimulationSpeedResponse)
async def set_simulation_speed(body: SetSimulationSpeedRequest, request: Request) -> SimulationSpeedResponse:
    """Command a new virtual-time speed multiplier (see SimulationEngine.set_speed_multiplier())."""
    state = _state(request)
    try:
        state.engine.set_speed_multiplier(body.speed_multiplier)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SimulationSpeedResponse(speed_multiplier=state.clock.speed_multiplier)


@router.post("/api/conveyor/speed", response_model=ConveyorStatusResponse)
async def set_conveyor_speed(body: SetConveyorSpeedRequest, request: Request) -> ConveyorStatusResponse:
    """Command a new target speed for the conveyor (see DrivenConveyorSegment.set_speed())."""
    state = _state(request)
    try:
        state.segment.set_speed(body.speed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ConveyorStatusResponse(speed=state.segment.speed, target_speed=state.segment.target_speed)


@router.get("/api/statistics", response_model=StatisticsResponse)
async def get_statistics(request: Request) -> StatisticsResponse:
    """Return the aggregate statistics summary (see README section 34)."""
    state = _state(request)
    return StatisticsResponse(**state.controller.statistics.summary(state.clock.now()))
