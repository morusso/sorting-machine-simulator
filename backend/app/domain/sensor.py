from abc import ABC, abstractmethod


class Sensor(ABC):
    """Interface for a binary presence/position sensor.

    Covers cases such as entry photoelectric sensors, package presence
    sensors, gate position sensors, end-of-belt sensors, and jam sensors.
    """

    @abstractmethod
    async def is_triggered(self) -> bool:
        """Return whether the sensor is currently triggered.

        Returns:
            True if the sensor currently detects a package/condition,
            False otherwise.
        """
        raise NotImplementedError
