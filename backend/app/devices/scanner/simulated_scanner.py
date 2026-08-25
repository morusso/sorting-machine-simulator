import random
from collections import deque

from app.domain.scanner import ScanEvent, Scanner, ScanResult


class SimulatedScanner(Scanner):
    def __init__(
        self,
        error_rate: float = 0.0,
        confidence: float = 0.98,
        rng: random.Random | None = None,
    ):
        self.error_rate = error_rate
        self.confidence = confidence
        self._rng = rng if rng is not None else random.Random()
        self._queue: deque[tuple[str, str, float | None]] = deque()
        self._scan_count = 0

    def enqueue(self, package_id: str, barcode: str, position: float | None = None) -> None:
        self._queue.append((package_id, barcode, position))

    async def scan(self) -> ScanResult:
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
