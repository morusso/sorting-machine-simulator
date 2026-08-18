class SimulationEngine:
    """Coordinates the clock and all simulated components.

    The engine is the central element of the simulation: it drives the
    Clock and steps the conveyor, scanner, encoder, sensors, gates, and
    controller in sync, and exposes start/pause/resume/stop/reset controls
    plus adjustable simulation speed.
    """

    def start(self):
        """Start the simulation from its current (or initial) state."""
        raise NotImplementedError

    def pause(self):
        """Pause the simulation, preserving current state."""
        raise NotImplementedError

    def resume(self):
        """Resume a previously paused simulation."""
        raise NotImplementedError

    def stop(self):
        """Stop the simulation."""
        raise NotImplementedError

    def reset(self):
        """Reset the simulation to its initial state."""
        raise NotImplementedError
