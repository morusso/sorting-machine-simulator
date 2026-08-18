class Clock:
    """Tracks simulation time, distinct from real (wall-clock) time.

    A speed_multiplier greater than 1.0 lets simulation time advance
    faster than real time, so tests can run many cycles quickly.

    Attributes:
        speed_multiplier: Ratio of simulated seconds to real seconds
            (e.g. 10.0 means 1 real second equals 10 simulated seconds).
    """

    def __init__(self, speed_multiplier: float = 1.0):
        """Initialize the clock.

        Args:
            speed_multiplier: Ratio of simulated seconds to real seconds.
        """
        self.speed_multiplier = speed_multiplier

    def now(self) -> float:
        """Return the current simulation time.

        Returns:
            The current simulation time, in seconds.
        """
        raise NotImplementedError
