class Clock:
    """Tracks simulation time, distinct from real (wall-clock) time."""

    def __init__(self, speed_multiplier: float = 1.0):
        self.speed_multiplier = speed_multiplier

    def now(self) -> float:
        raise NotImplementedError
