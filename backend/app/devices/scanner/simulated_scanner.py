import random
from collections.abc import Callable

from app.domain.scanner import ScanEvent, Scanner, ScanResult


class SimulatedScanner(Scanner):
    """Scanner that "reads" a package's code from an injected lookup rather
    than a camera.

    barcode_lookup stands in for the physical label a real scanner would
    read optically — it is simulation-only data, which is exactly why it
    is supplied once at construction (see app.domain.device_factory)
    rather than passed into scan() itself; scan() only ever receives what
    a real caller could legitimately supply (see Scanner.scan()).

    Attributes:
        error_rate: Probability, in [0, 1], that a scan attempt fails to
            find a code (see README section 7).
        confidence: Read confidence reported for successful scans.
    """

    def __init__(
        self,
        barcode_lookup: Callable[[str], str | None],
        error_rate: float = 0.0,
        confidence: float = 0.98,
        rng: random.Random | None = None,
    ):
        """Initialize a simulated scanner.

        Args:
            barcode_lookup: Given a package_id, returns that package's
                true barcode (or None if unknown to the caller).
            error_rate: Probability, in [0, 1], that a scan attempt fails
                to find a code.
            confidence: Read confidence reported for successful scans.
            rng: Random source used to decide scan outcomes. Inject a
                seeded random.Random for deterministic tests; defaults to
                a fresh, unseeded generator.
        """
        self._barcode_lookup = barcode_lookup
        self.error_rate = error_rate
        self.confidence = confidence
        self._rng = rng if rng is not None else random.Random()
        self._scan_count = 0

    async def scan(self, package_id: str, position: float | None = None) -> ScanResult:
        """Attempt to read package_id's code via barcode_lookup.

        Args:
            package_id: Identifier of the package to read, looked up via
                barcode_lookup.
            position: Package position along the transport axis at scan
                time, in meters, if known.

        Returns:
            The result of the scan attempt: CODE_DETECTED with the
            package's barcode, or CODE_NOT_FOUND if the simulated error
            rate triggered a failed read or barcode_lookup has no code for
            this package_id.
        """
        self._scan_count += 1
        scan_id = f"SCAN-{self._scan_count:06d}"
        barcode = self._barcode_lookup(package_id)

        if barcode is None or self._rng.random() < self.error_rate:
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
