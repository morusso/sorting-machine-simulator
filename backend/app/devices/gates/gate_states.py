"""State Pattern implementation backing SimulatedGate (see GateState).

Each concrete _GateStateHandler encapsulates the behavior of one
GateState: which commands are valid from it, and what state (if any) a
command or the passage of simulated time transitions it to. SimulatedGate
holds only a reference to its current handler and delegates every command
to it, rather than checking `self._state == X` throughout its own methods.

States are stateless (all per-gate data — clock, timers, configured
durations — lives on the SimulatedGate passed into each method), so each
one is a module-level singleton rather than instantiated per gate.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.domain.gate import GateState

if TYPE_CHECKING:
    from app.devices.gates.simulated_gate import SimulatedGate


class _GateStateHandler:
    """Base handler: refuses every command, from an unnamed state.

    Concrete subclasses override `value` and only the commands valid from
    that state; the rest keep raising via this base implementation.
    """

    value: GateState

    def resolve(self, gate: SimulatedGate) -> _GateStateHandler:
        """Return the handler to transition to now, based on elapsed simulated time.

        The default is that nothing changes on its own — only OPENING and
        CLOSING auto-transition once their configured duration has passed.

        Args:
            gate: The gate whose clock/timers to check against.

        Returns:
            self, or the handler for the state reached automatically.
        """
        return self

    def open(self, gate: SimulatedGate) -> _GateStateHandler:
        """Handle an open() command. Raises unless overridden.

        Args:
            gate: The gate the command was issued on.

        Raises:
            RuntimeError: Always, from a state where opening isn't valid.
        """
        raise RuntimeError(f"cannot open gate from state {self.value}")

    def close(self, gate: SimulatedGate) -> _GateStateHandler:
        """Handle a close() command. Raises unless overridden.

        Args:
            gate: The gate the command was issued on.

        Raises:
            RuntimeError: Always, from a state where closing isn't valid.
        """
        raise RuntimeError(f"cannot close gate from state {self.value}")

    def simulate_error(self, gate: SimulatedGate) -> _GateStateHandler:
        """Handle a simulate_error() command. Raises unless overridden.

        Args:
            gate: The gate the command was issued on.

        Raises:
            RuntimeError: Always, from a state where failing isn't valid.
        """
        raise RuntimeError(f"cannot fail gate from state {self.value}")


class _Closed(_GateStateHandler):
    value = GateState.CLOSED

    def open(self, gate: SimulatedGate) -> _GateStateHandler:
        gate._transition_start = gate._clock.now()
        return _OPENING


class _Opening(_GateStateHandler):
    value = GateState.OPENING

    def resolve(self, gate: SimulatedGate) -> _GateStateHandler:
        elapsed_ms = (gate._clock.now() - gate._transition_start) * 1000
        if elapsed_ms >= gate.open_time_ms:
            gate._transition_start = None
            return _OPEN
        return self

    def simulate_error(self, gate: SimulatedGate) -> _GateStateHandler:
        gate._transition_start = None
        return _ERROR


class _Open(_GateStateHandler):
    value = GateState.OPEN

    def close(self, gate: SimulatedGate) -> _GateStateHandler:
        gate._transition_start = gate._clock.now()
        return _CLOSING


class _Closing(_GateStateHandler):
    value = GateState.CLOSING

    def resolve(self, gate: SimulatedGate) -> _GateStateHandler:
        elapsed_ms = (gate._clock.now() - gate._transition_start) * 1000
        if elapsed_ms >= gate.close_time_ms:
            gate._transition_start = None
            return _CLOSED
        return self

    def simulate_error(self, gate: SimulatedGate) -> _GateStateHandler:
        gate._transition_start = None
        return _ERROR


class _Error(_GateStateHandler):
    value = GateState.ERROR


_CLOSED = _Closed()
_OPENING = _Opening()
_OPEN = _Open()
_CLOSING = _Closing()
_ERROR = _Error()

INITIAL_STATE = _CLOSED
