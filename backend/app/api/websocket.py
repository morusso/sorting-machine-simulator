from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.simulation.sorting_line import SortingLine

router = APIRouter()


class ConnectionManager:
    """Tracks connected WebSocket clients and broadcasts state to them.

    See README section 31: the frontend receives the machine state over
    WebSocket rather than polling the REST API.
    """

    def __init__(self):
        """Initialize with no connected clients."""
        self._clients: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and start tracking a client connection.

        Args:
            websocket: The client connection to accept.
        """
        await websocket.accept()
        self._clients.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Stop tracking a client connection.

        Args:
            websocket: The client connection to drop.
        """
        self._clients.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to every connected client.

        Clients that fail to receive it (e.g. already disconnected) are
        dropped rather than raising.

        Args:
            message: The JSON-serializable message to send.
        """
        for websocket in list(self._clients):
            try:
                await websocket.send_json(message)
            except Exception:
                self.disconnect(websocket)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Stream simulation_state messages to a connected client.

    The client isn't expected to send anything; this just holds the
    connection open until it disconnects (see README section 31).
    """
    manager: ConnectionManager = websocket.app.state.connection_manager
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def broadcast_state(websocket_app_state, simulation: SortingLine) -> None:
    """Broadcast the current simulation snapshot to all connected clients.

    Args:
        websocket_app_state: The FastAPI app's `state` object, expected to
            carry a `connection_manager` (see main.py's lifespan setup).
        simulation: The simulation to snapshot and broadcast.
    """
    manager: ConnectionManager = websocket_app_state.connection_manager
    await manager.broadcast(await simulation.snapshot())
