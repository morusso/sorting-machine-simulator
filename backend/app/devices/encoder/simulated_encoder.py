from app.domain.conveyor import DrivenConveyorSegment
from app.domain.encoder import Encoder


class SimulatedEncoder(Encoder):
    def __init__(
        self,
        conveyor: DrivenConveyorSegment,
        resolution: int = 1000,
        wheel_circumference: float = 0.5,
    ):
        self._conveyor = conveyor
        self.resolution = resolution
        self.wheel_circumference = wheel_circumference

    async def get_pulse_count(self) -> int:

        pulses_per_meter = self.resolution / self.wheel_circumference
        return round(self._conveyor.total_distance * pulses_per_meter)
