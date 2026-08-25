class Clock:

    def __init__(self, speed_multiplier: float = 1.0):

        self.speed_multiplier = speed_multiplier
        self._elapsed = 0.0
        self._paused = False

    def now(self) -> float:

        return self._elapsed

    @property
    def is_paused(self) -> bool:
        return self._paused

    def advance(self, real_dt: float) -> None:

        if real_dt < 0:
            raise ValueError("real_dt must be non-negative")
        if self._paused:
            return
        self._elapsed += real_dt * self.speed_multiplier

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def reset(self) -> None:

        self._elapsed = 0.0
        self._paused = False
