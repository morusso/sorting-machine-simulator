from abc import ABC, abstractmethod
from enum import Enum


class GateState(str, Enum):
    """Lifecycle states of a sorting gate.

    Valid transitions are: CLOSED -> OPENING -> OPEN -> CLOSING -> CLOSED,
    with OPENING and CLOSING also able to transition to ERROR.
    """

    CLOSED = "CLOSED"
    OPENING = "OPENING"
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    ERROR = "ERROR"


class Gate(ABC):
    """Interface for a sorting gate actuator.

    Implementations may be simulated or backed by real hardware (e.g. via
    a PLC), but expose the same interface so the controller does not need
    to know which one it is driving.
    """

    @abstractmethod
    async def open(self):
        """Command the gate to open.

        The gate does not open instantly; its state transitions through
        OPENING before reaching OPEN (see GateState).
        """
        raise NotImplementedError

    @abstractmethod
    async def close(self):
        """Command the gate to close.

        The gate does not close instantly; its state transitions through
        CLOSING before reaching CLOSED (see GateState).
        """
        raise NotImplementedError

    @abstractmethod
    async def get_state(self) -> GateState:
        """Return the gate's current state.

        Returns:
            The gate's current GateState.
        """
        raise NotImplementedError
