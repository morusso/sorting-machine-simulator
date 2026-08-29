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
    know which one it is talking to. Note what scan() deliberately does
    *not* take: the code to expect. A real scanner discovers the code
    optically — it can never be told the answer in advance — so no
    implementation of this interface may depend on being handed one (see
    README section 37: "the scanner is replaceable without changes to the
    sorting logic").
    """

    @abstractmethod
    async def scan(self, package_id: str, position: float | None = None) -> ScanResult:
        """Attempt to read whatever code is currently in front of this scanner.

        Args:
            package_id: Identifier to tag the result with. Supplied by
                whatever triggers the read (e.g. a photoelectric sensor
                paired with the caller's own position tracking, see
                README section 6) — a scanner has no way to know a
                package's identity from a barcode read alone, since that's
                precisely what the read is for.
            position: Package position along the transport axis at scan
                time, in meters, if known. Echoed into the result.

        Returns:
            The result of the scan attempt.
        """
        raise NotImplementedError
