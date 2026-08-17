from abc import ABC, abstractmethod
from enum import Enum


class GateState(str, Enum):
    CLOSED = "CLOSED"
    OPENING = "OPENING"
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    ERROR = "ERROR"


class Gate(ABC):
    @abstractmethod
    async def open(self):
        raise NotImplementedError

    @abstractmethod
    async def close(self):
        raise NotImplementedError

    @abstractmethod
    async def get_state(self) -> GateState:
        raise NotImplementedError
