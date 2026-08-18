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
