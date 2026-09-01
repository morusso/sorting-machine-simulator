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
        self.faulted = False
        self._frozen_pulse_count = 0

    async def get_pulse_count(self) -> int:
        """Return the cumulative number of pulses generated so far.

        Returns:
            The total pulse count implied by the conveyor's belt travel
            since the segment was created, or the pulse count frozen at
            the moment of simulate_error() if the encoder is faulted.
        """
        if self.faulted:
            return self._frozen_pulse_count
        return round(self._conveyor.total_distance * self.pulses_per_meter)

    def simulate_error(self) -> None:
        """Force the encoder into a faulted state (ENCODER_ERROR).

        Freezes get_pulse_count() at its current value, as if the encoder
        wheel had disconnected from the belt — the belt keeps moving but
        the encoder stops reporting it. There is no way back other than
        rebuilding the encoder (see SortingLine.reset()).
        """
        self._frozen_pulse_count = round(self._conveyor.total_distance * self.pulses_per_meter)
        self.faulted = True

    @property
    def pulses_per_meter(self) -> float:
        """Encoder pulses per meter of belt travel, from resolution/wheel_circumference."""
        return self.resolution / self.wheel_circumference
