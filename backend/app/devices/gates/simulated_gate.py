from app.devices.gates.gate_states import INITIAL_STATE, _GateStateHandler
from app.domain.gate import Gate, GateState
from app.simulation.clock import Clock


class SimulatedGate(Gate):
    """A sorting gate whose OPENING/CLOSING transitions take simulated time.

    Delegates every command (open/close/simulate_error) and state
    resolution to a _GateStateHandler (see app.devices.gates.gate_states,
    State Pattern), so the valid-transition rules for each GateState live
    with that state rather than as guard conditions scattered across this
    class. State is resolved lazily from the clock rather than advanced by
    a ticking loop: get_state() (and open()/close()) compute the current
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
        self._state: _GateStateHandler = INITIAL_STATE
        self._transition_start: float | None = None

    def _resolve_state(self) -> _GateStateHandler:
        """Advance a pending OPENING/CLOSING transition if it has finished.

        Returns:
            The gate's up-to-date state handler.
        """
        self._state = self._state.resolve(self)
        return self._state

    async def open(self):
        """Command the gate to open.

        Raises:
            RuntimeError: If the gate is not currently CLOSED.
        """
        self._state = self._resolve_state().open(self)

    async def close(self):
        """Command the gate to close.

        Raises:
            RuntimeError: If the gate is not currently OPEN.
        """
        self._state = self._resolve_state().close(self)

    async def get_state(self) -> GateState:
        """Return the gate's current state, resolving any finished transition.

        Returns:
            The gate's current GateState.
        """
        return self._resolve_state().value

    def simulate_error(self) -> None:
        """Force the gate into ERROR, as if the actuator failed mid-transition.

        Raises:
            RuntimeError: If the gate is not currently OPENING or CLOSING.
        """
        self._state = self._resolve_state().simulate_error(self)
