"""EngineState and the State Pattern implementation backing SimulationEngine.

Each concrete _EngineStateHandler encapsulates the behavior of one
EngineState: which lifecycle commands are valid from it, what state a
command transitions to, and whether segments should advance on tick()
while in it. SimulationEngine holds only a reference to its current
handler and delegates every command to it, rather than checking
`self.state == X` throughout its own methods.

States are stateless (all per-engine data — the clock — lives on the
SimulationEngine passed into each method), so each one is a module-level
singleton rather than instantiated per engine.
"""

from __future__ import annotations

from enum import Enum

from app.simulation.clock import Clock


class EngineState(str, Enum):
    """Lifecycle states of the SimulationEngine.

    Valid transitions are: STOPPED -> RUNNING -> PAUSED -> RUNNING, and
    RUNNING/PAUSED -> STOPPED.
    """

    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"


class _EngineStateHandler:
    """Base handler: refuses every lifecycle command, and does not tick.

    Concrete subclasses override `value` and only the commands valid from
    that state; the rest keep raising via this base implementation.
    """

    value: EngineState
    advances_on_tick: bool = False

    def start(self, clock: Clock) -> _EngineStateHandler:
        """Handle a start() command. Raises unless overridden.

        Args:
            clock: The engine's clock, to resume/pause as appropriate.

        Raises:
            RuntimeError: Always, from a state where starting isn't valid.
        """
        raise RuntimeError(f"cannot start engine from state {self.value}")

    def pause(self, clock: Clock) -> _EngineStateHandler:
        """Handle a pause() command. Raises unless overridden.

        Args:
            clock: The engine's clock, to resume/pause as appropriate.

        Raises:
            RuntimeError: Always, from a state where pausing isn't valid.
        """
        raise RuntimeError(f"cannot pause engine from state {self.value}")

    def resume(self, clock: Clock) -> _EngineStateHandler:
        """Handle a resume() command. Raises unless overridden.

        Args:
            clock: The engine's clock, to resume/pause as appropriate.

        Raises:
            RuntimeError: Always, from a state where resuming isn't valid.
        """
        raise RuntimeError(f"cannot resume engine from state {self.value}")

    def stop(self, clock: Clock) -> _EngineStateHandler:
        """Handle a stop() command. Raises unless overridden.

        Args:
            clock: The engine's clock, to resume/pause as appropriate.

        Raises:
            RuntimeError: Always, from a state where stopping isn't valid.
        """
        raise RuntimeError(f"cannot stop engine from state {self.value}")


class _Stopped(_EngineStateHandler):
    value = EngineState.STOPPED

    def start(self, clock: Clock) -> _EngineStateHandler:
        clock.resume()
        return _RUNNING


class _Running(_EngineStateHandler):
    value = EngineState.RUNNING
    advances_on_tick = True

    def pause(self, clock: Clock) -> _EngineStateHandler:
        clock.pause()
        return _PAUSED

    def stop(self, clock: Clock) -> _EngineStateHandler:
        clock.pause()
        return _STOPPED


class _Paused(_EngineStateHandler):
    value = EngineState.PAUSED

    def resume(self, clock: Clock) -> _EngineStateHandler:
        clock.resume()
        return _RUNNING

    def stop(self, clock: Clock) -> _EngineStateHandler:
        clock.pause()
        return _STOPPED


_STOPPED = _Stopped()
_RUNNING = _Running()
_PAUSED = _Paused()

INITIAL_STATE = _STOPPED
