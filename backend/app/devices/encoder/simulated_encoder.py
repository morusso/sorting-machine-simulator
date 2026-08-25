from app.domain.conveyor import DrivenConveyorSegment
from app.domain.encoder import Encoder


class SimulatedEncoder(Encoder):
    """Encoder driven by a DrivenConveyorSegment's belt travel.

    Pulse count is derived from the segment's total_distance rather than
    tracked independently, so it stays in sync with the belt regardless of
    speed changes.

    Attributes:
        resolution: Encoder resolution, in pulses per wheel revolution.
        wheel_circumference: Encoder wheel circumference, in meters.
    """

    def __init__(
        self,
        conveyor: DrivenConveyorSegment,
        resolution: int = 1000,
        wheel_circumference: float = 0.5,
    ):
        """Initialize an encoder bound to a driven conveyor segment.

        Args:
            conveyor: The driven segment whose belt travel this encoder
                tracks.
            resolution: Encoder resolution, in pulses per wheel revolution.
            wheel_circumference: Encoder wheel circumference, in meters.
        """
        self._conveyor = conveyor
        self.resolution = resolution
        self.wheel_circumference = wheel_circumference

    async def get_pulse_count(self) -> int:
        """Return the cumulative number of pulses generated so far.

        Returns:
            The total pulse count implied by the conveyor's belt travel
            since the segment was created.
        """
        pulses_per_meter = self.resolution / self.wheel_circumference
        return round(self._conveyor.total_distance * pulses_per_meter)
