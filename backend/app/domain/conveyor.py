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

    async def get_package_position(self, package_id: str) -> float:
        """Return the current position of a package on this segment.

        Args:
            package_id: Identifier of the package to locate.

        Returns:
            The package's position along the segment, in meters.
        """
        raise NotImplementedError
