"""FastAPI application entry point (see README section 18, Technology Stack)."""

import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.orders import router as orders_router
from app.api.routes import router as rest_router
from app.api.websocket import ConnectionManager
from app.api.websocket import broadcast_state
from app.api.websocket import router as websocket_router
from app.simulation.sorting_line import SortingLine
from app.storage.database import create_engine, create_session_factory, init_models

TICK_INTERVAL_S = 0.1
"""How often the background loop advances the simulation and broadcasts
state, in real seconds (see README section 20-21)."""


async def _simulation_loop(app: FastAPI) -> None:
    """Tick the simulation and broadcast its state on a fixed real-time interval."""
    while True:
        await asyncio.sleep(TICK_INTERVAL_S)
        await app.state.simulation.tick(TICK_INTERVAL_S)
        await broadcast_state(app.state, app.state.simulation)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Wire up simulation state and start/stop the background tick loop."""
    app.state.simulation = SortingLine()
    app.state.connection_manager = ConnectionManager()
    app.state.db_engine = create_engine()
    await init_models(app.state.db_engine)
    app.state.db_sessionmaker = create_session_factory(app.state.db_engine)
    task = asyncio.create_task(_simulation_loop(app))
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        await app.state.db_engine.dispose()


app = FastAPI(title="Sorting Machine Simulator", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(rest_router)
app.include_router(orders_router)
app.include_router(websocket_router)
