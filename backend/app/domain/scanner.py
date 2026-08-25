from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel


class ScanEvent(str, Enum):
    """Outcome of a single scan attempt (see README sections 6-7)."""

    CODE_DETECTED = "CODE_DETECTED"
    CODE_NOT_FOUND = "CODE_NOT_FOUND"


class ScanResult(BaseModel):
    """Result of a single scan attempt.

    Attributes:
        event: Whether a code was detected or not.
        scan_id: Unique identifier of this scan attempt (e.g. "SCAN-000001").
        package_id: Identifier of the package that was scanned.
        code: Decoded barcode value. None when event is CODE_NOT_FOUND.
        position: Package position along the transport axis at scan time,
            in meters, if known.
        confidence: Read confidence in [0, 1]. None when event is
            CODE_NOT_FOUND.
    """

    event: ScanEvent
    scan_id: str
    package_id: str
    code: str | None = None
    position: float | None = None
    confidence: float | None = None


class Scanner(ABC):
    """Interface for a barcode/QR/Data Matrix code reader.

    Implementations may be simulated or backed by a real device (e.g. over
    TCP), but expose the same interface so the controller does not need to
    know which one it is talking to.
    """

    @abstractmethod
    async def scan(self) -> ScanResult:
        """Read the next available code.

        Returns:
            The result of the scan attempt.
        """
        raise NotImplementedError
