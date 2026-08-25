class Clock:
    """Simulation clock tracking elapsed simulated time.

    Simulated time advances only when advance() is called explicitly and
    the clock is not paused, letting callers drive it from either a
    real-time loop or an accelerated/test-controlled one.

    Attributes:
        speed_multiplier: Factor applied to each advance() call, e.g. 10.0
            means 1 real second of advance() calls represents 10 simulated
            seconds (see README section 21, Virtual Time).
    """

    def __init__(self, speed_multiplier: float = 1.0):
        """Initialize a clock at time zero, running.

        Args:
            speed_multiplier: Factor applied to each advance() call.
        """
        self.speed_multiplier = speed_multiplier
        self._elapsed = 0.0
        self._paused = False

    def now(self) -> float:
        """Return the current simulated time.

        Returns:
            Elapsed simulated time, in seconds, since the clock was
            created or last reset.
        """
        return self._elapsed

    @property
    def is_paused(self) -> bool:
        """Whether the clock is currently paused."""
        return self._paused

    def advance(self, real_dt: float) -> None:
        """Advance simulated time by real_dt * speed_multiplier.

        No-op while the clock is paused.

        Args:
            real_dt: Elapsed real (wall-clock) time to advance by, in
                seconds.

        Raises:
            ValueError: If real_dt is negative.
        """
        if real_dt < 0:
            raise ValueError("real_dt must be non-negative")
        if self._paused:
            return
        self._elapsed += real_dt * self.speed_multiplier

    def pause(self) -> None:
        """Pause the clock, causing advance() to become a no-op."""
        self._paused = True

    def resume(self) -> None:
        """Resume the clock, letting advance() accumulate time again."""
        self._paused = False

    def reset(self) -> None:
        """Reset elapsed time to zero and resume the clock."""
        self._elapsed = 0.0
        self._paused = False
