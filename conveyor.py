from abc import ABC, abstractmethod


class ConveyorSegment(ABC):
    """Shared position/velocity interface for driven and gravity segments."""

    @abstractmethod
    async def get_package_position(self, package_id: str) -> float:
        raise NotImplementedError


class DrivenConveyorSegment(ConveyorSegment):
    def __init__(self, length: float, speed: float, max_speed: float, acceleration: float):
        self.length = length
        self.speed = speed
        self.max_speed = max_speed
        self.acceleration = acceleration

    async def get_package_position(self, package_id: str) -> float:
        raise NotImplementedError
