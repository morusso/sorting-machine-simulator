from app.domain.sensor import Sensor


class SimulatedSensor(Sensor):
    def __init__(self, sensor_id: str):
        self.sensor_id = sensor_id
        self._triggered = False

    def trigger(self) -> None:
        self._triggered = True

    def clear(self) -> None:
        self._triggered = False

    async def is_triggered(self) -> bool:

        return self._triggered
