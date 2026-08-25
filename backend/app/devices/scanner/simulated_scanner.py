import random
from collections import deque

from app.domain.scanner import ScanEvent, Scanner, ScanResult


class SimulatedScanner(Scanner):
    """Scanner that reads codes from a queue of packages fed to it.

    Something with visibility into package positions (e.g. a future
    PackageManager) is expected to call enqueue() as packages reach the
    scanner's location; scan() then reports a read for the next one.

    Attributes:
        error_rate: Probability, in [0, 1], that a scan attempt fails to
            find a code (see README section 7).
        confidence: Read confidence reported for successful scans.
    """

    def __init__(
        self,
        error_rate: float = 0.0,
        confidence: float = 0.98,
        rng: random.Random | None = None,
    ):
        """Initialize a simulated scanner with an empty queue.

        Args:
            error_rate: Probability, in [0, 1], that a scan attempt fails
                to find a code.
            confidence: Read confidence reported for successful scans.
            rng: Random source used to decide scan outcomes. Inject a
                seeded random.Random for deterministic tests; defaults to
                a fresh, unseeded generator.
        """
        self.error_rate = error_rate
        self.confidence = confidence
        self._rng = rng if rng is not None else random.Random()
        self._queue: deque[tuple[str, str, float | None]] = deque()
        self._scan_count = 0

    def enqueue(self, package_id: str, barcode: str, position: float | None = None) -> None:
        """Queue a package to be read by the next scan() call.

        Args:
            package_id: Identifier of the package reaching the scanner.
            barcode: The package's actual barcode value.
            position: Package position along the transport axis at scan
                time, in meters, if known.
        """
        self._queue.append((package_id, barcode, position))

    async def scan(self) -> ScanResult:
        """Read the next queued package's code.

        Returns:
            The result of the scan attempt: CODE_DETECTED with the
            package's barcode, or CODE_NOT_FOUND if the simulated error
            rate triggered a failed read.

        Raises:
            RuntimeError: If no package is queued for scanning.
        """
        if not self._queue:
            raise RuntimeError("no package queued for scanning")
        package_id, barcode, position = self._queue.popleft()
        self._scan_count += 1
        scan_id = f"SCAN-{self._scan_count:06d}"

        if self._rng.random() < self.error_rate:
            return ScanResult(
                event=ScanEvent.CODE_NOT_FOUND,
                scan_id=scan_id,
                package_id=package_id,
                position=position,
            )
        return ScanResult(
            event=ScanEvent.CODE_DETECTED,
            scan_id=scan_id,
            package_id=package_id,
            code=barcode,
            position=position,
            confidence=self.confidence,
        )
