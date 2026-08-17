from abc import ABC, abstractmethod


class Scanner(ABC):
    @abstractmethod
    async def scan(self):
        raise NotImplementedError
