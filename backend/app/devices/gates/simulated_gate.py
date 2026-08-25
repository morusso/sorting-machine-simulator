from app.domain.gate import Gate, GateState
from app.simulation.clock import Clock


class SimulatedGate(Gate):
    """A sorting gate whose OPENING/CLOSING transitions take simulated time.

    State is resolved lazily from the clock rather than advanced by a
    ticking loop: get_state() (and open()/close()) compute the current
    state from how much simulated time has elapsed since the last
    transition started.

    Attributes:
        open_time_ms: Time to transition from OPENING to OPEN, in
            milliseconds.
        close_time_ms: Time to transition from CLOSING to CLOSED, in
            milliseconds.
    """

    def __init__(self, clock: Clock, open_time_ms: float = 300, close_time_ms: float = 300):
        """Initialize a simulated gate, starting CLOSED.

        Args:
            clock: Simulation clock used to time OPENING/CLOSING
                transitions.
            open_time_ms: Time to transition from OPENING to OPEN, in
                milliseconds.
            close_time_ms: Time to transition from CLOSING to CLOSED, in
                milliseconds.
        """
        self._clock = clock
        self.open_time_ms = open_time_ms
        self.close_time_ms = close_time_ms
        self._state = GateState.CLOSED
        self._transition_start: float | None = None

    def _resolve_state(self) -> GateState:
        """Advance a pending OPENING/CLOSING transition if it has finished.

        Returns:
            The gate's up-to-date GateState.
        """
        if self._state in (GateState.OPENING, GateState.CLOSING):
            duration_ms = self.open_time_ms if self._state == GateState.OPENING else self.close_time_ms
            elapsed_ms = (self._clock.now() - self._transition_start) * 1000
            if elapsed_ms >= duration_ms:
                self._state = GateState.OPEN if self._state == GateState.OPENING else GateState.CLOSED
                self._transition_start = None
        return self._state

    async def open(self):
        """Command the gate to open.

        Raises:
            RuntimeError: If the gate is not currently CLOSED.
        """
        state = self._resolve_state()
        if state != GateState.CLOSED:
            raise RuntimeError(f"cannot open gate from state {state}")
        self._state = GateState.OPENING
        self._transition_start = self._clock.now()

    async def close(self):
        """Command the gate to close.

        Raises:
            RuntimeError: If the gate is not currently OPEN.
        """
        state = self._resolve_state()
        if state != GateState.OPEN:
            raise RuntimeError(f"cannot close gate from state {state}")
        self._state = GateState.CLOSING
        self._transition_start = self._clock.now()

    async def get_state(self) -> GateState:
        """Return the gate's current state, resolving any finished transition.

        Returns:
            The gate's current GateState.
        """
        return self._resolve_state()

    def simulate_error(self) -> None:
        """Force the gate into ERROR, as if the actuator failed mid-transition.

        Raises:
            RuntimeError: If the gate is not currently OPENING or CLOSING.
        """
        state = self._resolve_state()
        if state not in (GateState.OPENING, GateState.CLOSING):
            raise RuntimeError(f"cannot fail gate from state {state}")
        self._state = GateState.ERROR
        self._transition_start = None
