"""Domain events and a publish/subscribe hub (see README sections 24, 34).

Producers (e.g. Controller) publish events describing what happened,
without knowing who — if anyone — is listening. Consumers (e.g. Statistics)
subscribe to the event types they care about. This keeps Controller free of
any dependency on Statistics' recording API, so new consumers (logging, a
live event feed, ...) can be added without touching Controller.
"""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class PackageCreated:
    """A new package entered the system."""

    timestamp: float
    package_id: str


@dataclass(frozen=True)
class ScanErrored:
    """A scan attempt failed to find a code (CODE_NOT_FOUND)."""

    timestamp: float
    package_id: str


@dataclass(frozen=True)
class CodeDetected:
    """A scan attempt successfully decoded a barcode."""

    timestamp: float
    package_id: str
    code: str


@dataclass(frozen=True)
class UnknownCodeScanned:
    """A decoded barcode has no routing_table entry (UNKNOWN_BARCODE)."""

    timestamp: float
    package_id: str
    code: str


@dataclass(frozen=True)
class GateOpened:
    """A gate was triggered open for a package."""

    timestamp: float
    package_id: str
    gate_id: int


@dataclass(frozen=True)
class GateErrored:
    """A gate failed to open for a package (GATE_ERROR)."""

    timestamp: float
    package_id: str
    gate_id: int


@dataclass(frozen=True)
class PackageSorted:
    """A package reached its destination gate and was sorted."""

    timestamp: float
    package_id: str
    gate_id: int


@dataclass(frozen=True)
class DuplicateScanDetected:
    """A package was scanned again after already having been scanned (DUPLICATE_SCAN)."""

    timestamp: float
    package_id: str


@dataclass(frozen=True)
class PackageLost:
    """A package left the driven segment without reaching a terminal status (PACKAGE_LOST)."""

    timestamp: float
    package_id: str


@dataclass(frozen=True)
class GravitySegmentStalled:
    """A package stopped moving on the gravity segment on its own (GRAVITY_SEGMENT_STALL)."""

    timestamp: float
    package_id: str


@dataclass(frozen=True)
class GravitySegmentJammed:
    """A package was blocked by another package ahead of it on the gravity segment (GRAVITY_SEGMENT_JAM)."""

    timestamp: float
    package_id: str


@dataclass(frozen=True)
class ConveyorStopped:
    """The driven conveyor faulted and stopped outside of a commanded stop (CONVEYOR_STOPPED)."""

    timestamp: float


@dataclass(frozen=True)
class SensorErrored:
    """A sensor faulted and stopped reporting reliable readings (SENSOR_ERROR)."""

    timestamp: float
    sensor_id: str


@dataclass(frozen=True)
class EncoderErrored:
    """The encoder faulted and stopped reporting pulses (ENCODER_ERROR)."""

    timestamp: float


@dataclass(frozen=True)
class EmergencyStopped:
    """The controller entered SAFE_MODE (see README section 26, EMERGENCY_STOP)."""

    timestamp: float


class EventBus:
    """Synchronous publish/subscribe hub.

    Not thread-safe; expects to be driven by a single simulation loop, like
    the rest of the engine.
    """

    def __init__(self):
        """Initialize with no subscribers."""
        self._subscribers: dict[type, list[Callable[[object], None]]] = {}

    def subscribe(self, event_type: type, handler: Callable[[object], None]) -> None:
        """Register a handler to be called for every published event of event_type.

        Args:
            event_type: The event class to listen for.
            handler: Callable invoked with the event instance when published.
        """
        self._subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: object) -> None:
        """Notify every handler subscribed to this event's type.

        Args:
            event: The event instance to dispatch.
        """
        for handler in self._subscribers.get(type(event), []):
            handler(event)
