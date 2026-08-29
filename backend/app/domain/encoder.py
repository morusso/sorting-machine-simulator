from abc import ABC, abstractmethod


class Encoder(ABC):
    """Interface for a rotary encoder tracking a driven conveyor's motion.

    Pulse counts let the controller derive package position from actual
    belt movement rather than from elapsed time alone, which matters when
    belt speed changes.
    """

    @abstractmethod
    async def get_pulse_count(self) -> int:
        """Return the cumulative number of pulses generated so far.

        Returns:
            The total pulse count since the encoder was last reset.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def pulses_per_meter(self) -> float:
        """Calibration constant: encoder pulses per meter of belt travel.

        Lets a caller convert a delta in get_pulse_count() into a
        distance without knowing anything else about this encoder's
        implementation (see README section 37: the encoder should be
        replaceable without changes to the sorting algorithm).

        Returns:
            Encoder pulses per meter of belt travel.
        """
        raise NotImplementedError
