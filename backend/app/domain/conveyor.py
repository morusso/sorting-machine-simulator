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
        speed: Current belt speed, in m/s.
        max_speed: Maximum belt speed, in m/s.
        acceleration: Belt acceleration, in m/s^2.
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
            acceleration: Belt acceleration, in m/s^2.
        """
        self.length = length
        self.speed = speed
        self.max_speed = max_speed
        self.acceleration = acceleration
        self.total_distance = 0.0
        self._positions: dict[str, float] = {}

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
        """Move every tracked package forward by speed * dt.

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
        distance = self.speed * dt
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
