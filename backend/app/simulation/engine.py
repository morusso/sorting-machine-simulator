from app.simulation.clock import Clock
from app.simulation.engine_states import INITIAL_STATE, EngineState, _EngineStateHandler

__all__ = ["EngineState", "SimulationEngine"]


class SimulationEngine:
    """Controls the simulation's lifecycle and drives its clock.

    See README section 20; the engine is the central component that other
    simulated devices (conveyor, scanner, encoder, sensors, gates) are
    expected to be synchronized against.

    Delegates every lifecycle command (start/pause/resume/stop) to a
    _EngineStateHandler (see app.simulation.engine_states, State Pattern),
    so the valid-transition rules for each EngineState live with that
    state rather than as guard conditions scattered across this class.
    """

    def __init__(self, clock: Clock | None = None):
        """Initialize the engine in the STOPPED state.

        Args:
            clock: Clock to drive. Defaults to a fresh Clock() if not
                given, e.g. to allow tests to inject one with a custom
                speed_multiplier.
        """
        self.clock = clock if clock is not None else Clock()
        self._state: _EngineStateHandler = INITIAL_STATE
        self.segments: list = []

    @property
    def state(self) -> EngineState:
        """The engine's current lifecycle state."""
        return self._state.value

    def start(self):
        """Start the simulation, resuming the clock.

        Raises:
            RuntimeError: If the engine is not currently STOPPED.
        """
        self._state = self._state.start(self.clock)

    def pause(self):
        """Pause the simulation, freezing the clock.

        Raises:
            RuntimeError: If the engine is not currently RUNNING.
        """
        self._state = self._state.pause(self.clock)

    def resume(self):
        """Resume a paused simulation, unfreezing the clock.

        Raises:
            RuntimeError: If the engine is not currently PAUSED.
        """
        self._state = self._state.resume(self.clock)

    def stop(self):
        """Stop the simulation, freezing the clock at its current time.

        Raises:
            RuntimeError: If the engine is already STOPPED.
        """
        self._state = self._state.stop(self.clock)

    def reset(self):
        """Stop the simulation and reset the clock to time zero."""
        self.clock.reset()
        self._state = INITIAL_STATE

    def set_speed_multiplier(self, speed_multiplier: float) -> None:
        """Change the simulation's virtual-time speed (see README section
        20-21, "SPEED x1 / x2 / x10 / x100").

        Takes effect immediately, in any engine state, including mid-run.

        Args:
            speed_multiplier: New factor applied to each tick's elapsed
                simulated time, e.g. 10.0 means 1 real second of tick()
                calls advances the simulation by 10 seconds.

        Raises:
            ValueError: If speed_multiplier is not positive.
        """
        self.clock.set_speed_multiplier(speed_multiplier)

    def add_segment(self, segment) -> None:
        """Register a conveyor segment to be advanced on every tick().

        Args:
            segment: A DrivenConveyorSegment or GravityConveyorSegment (or
                any object exposing an advance(dt) method).
        """
        self.segments.append(segment)

    def tick(self, real_dt: float) -> float:
        """Advance the clock and every registered segment by one step.

        This is the bridge between the engine's lifecycle (see README
        section 20) and package motion: the clock's elapsed simulated
        time is fed straight into each registered segment's advance().
        A no-op beyond validating real_dt unless the engine is RUNNING —
        segments never move while STOPPED or PAUSED, regardless of the
        clock's own pause state (which reset() and a freshly constructed
        engine leave unpaused).

        Args:
            real_dt: Elapsed real (wall-clock) time since the last tick,
                in seconds.

        Returns:
            The simulated time actually advanced, in seconds. 0.0 if the
            engine is not RUNNING.

        Raises:
            ValueError: If real_dt is negative.
        """
        if real_dt < 0:
            raise ValueError("real_dt must be non-negative")
        if not self._state.advances_on_tick:
            return 0.0

        before = self.clock.now()
        self.clock.advance(real_dt)
        sim_dt = self.clock.now() - before
        for segment in self.segments:
            segment.advance(sim_dt)
        return sim_dt
