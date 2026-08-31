from abc import ABC, abstractmethod
from enum import Enum


class GateState(str, Enum):
    """Lifecycle states of a sorting gate.

    Valid transitions are: CLOSED -> OPENING -> OPEN -> CLOSING -> CLOSED,
    with OPENING and CLOSING also able to transition to ERROR. Every
    state can additionally transition to SAFE_STATE via emergency_stop()
    (see README section 26); unlike ERROR, this is a deliberate safety
    trip rather than a fault. Neither ERROR nor SAFE_STATE has a way back
    out other than rebuilding the gate (see SortingLine.reset()).
    """

    CLOSED = "CLOSED"
    OPENING = "OPENING"
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    ERROR = "ERROR"
    SAFE_STATE = "SAFE_STATE"


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

    @abstractmethod
    async def emergency_stop(self):
        """Force the gate into SAFE_STATE immediately (see README section 26).

        Unlike open()/close(), this must succeed from any current state
        and never raises — an emergency stop can never be refused.
        """
        raise NotImplementedError
