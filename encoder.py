from abc import ABC, abstractmethod


class Encoder(ABC):
    @abstractmethod
    async def get_pulse_count(self) -> int:
        raise NotImplementedError
