from app.domain.gate import Gate, GateState
from app.simulation.clock import Clock


class SimulatedGate(Gate):

    def __init__(self, clock: Clock, open_time_ms: float = 300, close_time_ms: float = 300):
        self._clock = clock
        self.open_time_ms = open_time_ms
        self.close_time_ms = close_time_ms
        self._state = GateState.CLOSED
        self._transition_start: float | None = None

    def _resolve_state(self) -> GateState:
        if self._state in (GateState.OPENING, GateState.CLOSING):
            duration_ms = self.open_time_ms if self._state == GateState.OPENING else self.close_time_ms
            elapsed_ms = (self._clock.now() - self._transition_start) * 1000
            if elapsed_ms >= duration_ms:
                self._state = GateState.OPEN if self._state == GateState.OPENING else GateState.CLOSED
                self._transition_start = None
        return self._state

    async def open(self):
        state = self._resolve_state()
        if state != GateState.CLOSED:
            raise RuntimeError(f"cannot open gate from state {state}")
        self._state = GateState.OPENING
        self._transition_start = self._clock.now()

    async def close(self):
        state = self._resolve_state()
        if state != GateState.OPEN:
            raise RuntimeError(f"cannot close gate from state {state}")
        self._state = GateState.CLOSING
        self._transition_start = self._clock.now()

    async def get_state(self) -> GateState:
        return self._resolve_state()

    def simulate_error(self) -> None:
        state = self._resolve_state()
        if state not in (GateState.OPENING, GateState.CLOSING):
            raise RuntimeError(f"cannot fail gate from state {state}")
        self._state = GateState.ERROR
        self._transition_start = None
