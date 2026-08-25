from abc import ABC, abstractmethod


class ConveyorSegment(ABC):
    """Shared position/velocity interface for driven and gravity segments.

    Controller and sorting logic depend only on this abstraction, so that a
    driven segment and a gravity segment (see GravityConveyorSegment) can be
    swapped or chained without changing higher-level code.
    """

    @abstractmethod
    async def get_package_position(self, package_id: str) -> float:
        """Return the current position of a package on this segment.

        Args:
            package_id: Identifier of the package to locate.

        Returns:
            The package's position along the segment, in meters.
        """
        raise NotImplementedError


class DrivenConveyorSegment(ConveyorSegment):
    """A motor-driven belt/roller conveyor segment.

    Attributes:
        length: Length of the segment, in meters.
        max_speed: Maximum belt speed, in m/s.
        acceleration: Belt acceleration/braking rate, in m/s^2. Limits how
            fast `speed` can change per second toward `target_speed`.
        target_speed: Speed the belt is ramping toward, in m/s. Set via
            set_speed(); advance() moves `speed` toward it by at most
            acceleration * dt.
        total_distance: Cumulative distance the belt has moved, in meters.
            Unlike package position, this is never clamped to the segment
            length — it reflects actual belt travel and backs the encoder's
            pulse count (see SimulatedEncoder).
    """

    def __init__(self, length: float, speed: float, max_speed: float, acceleration: float):
        """Initialize a driven conveyor segment.

        Args:
            length: Length of the segment, in meters.
            speed: Initial belt speed, in m/s.
            max_speed: Maximum allowed belt speed, in m/s.
            acceleration: Belt acceleration/braking rate, in m/s^2.
        """
        self.length = length
        self._speed = speed
        self.target_speed = speed
        self.max_speed = max_speed
        self.acceleration = acceleration
        self.total_distance = 0.0
        self._positions: dict[str, float] = {}

    @property
    def speed(self) -> float:
        """Current belt speed, in m/s."""
        return self._speed

    @speed.setter
    def speed(self, value: float) -> None:
        """Set the belt speed immediately, bypassing acceleration ramping.

        Also updates target_speed to match, so a subsequent advance() call
        does not ramp back toward a stale target. Prefer set_speed() to
        change speed gradually, as a real motor would (see README section
        4.1, "speed, acceleration, braking").

        Args:
            value: The belt speed to apply immediately, in m/s.
        """
        self._speed = value
        self.target_speed = value

    def set_speed(self, target_speed: float) -> None:
        """Command a new target speed, to be reached gradually via acceleration.

        Args:
            target_speed: Desired belt speed, in m/s.

        Raises:
            ValueError: If target_speed is negative or exceeds max_speed.
        """
        if target_speed < 0:
            raise ValueError("target_speed must be non-negative")
        if target_speed > self.max_speed:
            raise ValueError(f"target_speed must not exceed max_speed ({self.max_speed})")
        self.target_speed = target_speed

    def emergency_stop(self) -> None:
        """Immediately stop the belt, bypassing acceleration ramping.

        See README section 26: a driven conveyor's reaction to
        EMERGENCY_STOP is to stop outright, not to brake gradually.
        """
        self.speed = 0.0

    def add_package(self, package_id: str, position: float = 0.0) -> None:
        """Start tracking a package on this segment.

        Args:
            package_id: Identifier of the package entering the segment.
            position: Initial position along the segment, in meters.
        """
        self._positions[package_id] = position

    def remove_package(self, package_id: str) -> None:
        """Stop tracking a package on this segment (e.g. it exits onto the
        next segment or through a gate).

        Args:
            package_id: Identifier of the package leaving the segment.

        Raises:
            KeyError: If the package is not currently on this segment.
        """
        del self._positions[package_id]

    def advance(self, dt: float) -> None:
        """Ramp speed toward target_speed, then move packages accordingly.

        Speed changes by at most acceleration * dt toward target_speed
        (never overshooting it), and packages move by the average of the
        speed before and after this step, so a change in target_speed
        gradually affects motion rather than teleporting it.

        Positions are clamped to the segment length — a package that
        reaches the end holds there until removed (e.g. handed off to the
        next segment by the controller).

        Args:
            dt: Elapsed simulation time to advance by, in seconds.

        Raises:
            ValueError: If dt is negative.
        """
        if dt < 0:
            raise ValueError("dt must be non-negative")

        old_speed = self._speed
        if self._speed < self.target_speed:
            self._speed = min(self._speed + self.acceleration * dt, self.target_speed)
        elif self._speed > self.target_speed:
            self._speed = max(self._speed - self.acceleration * dt, self.target_speed)

        distance = 0.5 * (old_speed + self._speed) * dt
        self.total_distance += distance
        for package_id, position in self._positions.items():
            self._positions[package_id] = min(position + distance, self.length)

    async def get_package_position(self, package_id: str) -> float:
        """Return the current position of a package on this segment.

        Args:
            package_id: Identifier of the package to locate.

        Returns:
            The package's position along the segment, in meters.

        Raises:
            KeyError: If the package is not currently on this segment.
        """
        return self._positions[package_id]
