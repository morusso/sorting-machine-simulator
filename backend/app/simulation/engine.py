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


class SimulationEngine:
    """Controls the simulation's lifecycle and drives its clock.

    See README section 20; the engine is the central component that other
    simulated devices (conveyor, scanner, encoder, sensors, gates) are
    expected to be synchronized against.
    """

    def __init__(self, clock: Clock | None = None):
        """Initialize the engine in the STOPPED state.

        Args:
            clock: Clock to drive. Defaults to a fresh Clock() if not
                given, e.g. to allow tests to inject one with a custom
                speed_multiplier.
        """
        self.clock = clock if clock is not None else Clock()
        self.state = EngineState.STOPPED

    def start(self):
        """Start the simulation, resuming the clock.

        Raises:
            RuntimeError: If the engine is not currently STOPPED.
        """
        if self.state != EngineState.STOPPED:
            raise RuntimeError(f"cannot start engine from state {self.state}")
        self.clock.resume()
        self.state = EngineState.RUNNING

    def pause(self):
        """Pause the simulation, freezing the clock.

        Raises:
            RuntimeError: If the engine is not currently RUNNING.
        """
        if self.state != EngineState.RUNNING:
            raise RuntimeError(f"cannot pause engine from state {self.state}")
        self.clock.pause()
        self.state = EngineState.PAUSED

    def resume(self):
        """Resume a paused simulation, unfreezing the clock.

        Raises:
            RuntimeError: If the engine is not currently PAUSED.
        """
        if self.state != EngineState.PAUSED:
            raise RuntimeError(f"cannot resume engine from state {self.state}")
        self.clock.resume()
        self.state = EngineState.RUNNING

    def stop(self):
        """Stop the simulation, freezing the clock at its current time.

        Raises:
            RuntimeError: If the engine is already STOPPED.
        """
        if self.state == EngineState.STOPPED:
            raise RuntimeError(f"cannot stop engine from state {self.state}")
        self.clock.pause()
        self.state = EngineState.STOPPED

    def reset(self):
        """Stop the simulation and reset the clock to time zero."""
        self.clock.reset()
        self.state = EngineState.STOPPED
