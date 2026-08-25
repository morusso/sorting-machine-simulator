from app.domain.sensor import Sensor


class SimulatedSensor(Sensor):
    """A binary presence/position sensor with externally set state.

    Covers entry photoelectric sensors, package presence sensors, gate
    position sensors, end-of-belt sensors, and jam sensors alike (see
    README section 10). Something with visibility into package positions
    (e.g. a future PackageManager) is expected to call trigger()/clear()
    as packages move past the sensor's location.
    """

    def __init__(self, sensor_id: str):
        """Initialize a simulated sensor, starting untriggered.

        Args:
            sensor_id: Identifier of this sensor (e.g. "SENSOR-01").
        """
        self.sensor_id = sensor_id
        self._triggered = False

    def trigger(self) -> None:
        """Mark the sensor as currently detecting a package/condition."""
        self._triggered = True

    def clear(self) -> None:
        """Mark the sensor as no longer detecting a package/condition."""
        self._triggered = False

    async def is_triggered(self) -> bool:
        """Return whether the sensor is currently triggered.

        Returns:
            True if the sensor currently detects a package/condition,
            False otherwise.
        """
        return self._triggered
