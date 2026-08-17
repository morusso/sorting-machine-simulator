from abc import ABC, abstractmethod


class Sensor(ABC):
    @abstractmethod
    async def is_triggered(self) -> bool:
        raise NotImplementedError
