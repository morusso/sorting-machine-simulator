"""Event log and aggregate statistics (see README sections 24 and 34)."""

from dataclasses import dataclass


@dataclass
class Event:
    """A single logged simulation event (see README section 24).

    Attributes:
        timestamp: Simulated time the event occurred, in seconds.
        event_type: Short event name, e.g. "PACKAGE_SORTED".
        package_id: Identifier of the package the event concerns, if any.
        detail: Free-form extra context, e.g. a gate id or barcode.
    """

    timestamp: float
    event_type: str
    package_id: str | None = None
    detail: str | None = None


@dataclass
class _PackageTiming:
    """Timestamps used to derive average_scan_time/average_sort_time."""

    created_at: float
    scanned_at: float | None = None
    sorted_at: float | None = None


class Statistics:
    """Collects an event log and derives the aggregate counters/timings.

    Fed by the Controller as packages move through the system (see README
    sections 24-25, 34). Not thread-safe; expects to be driven by a single
    simulation loop, like the rest of the engine.
    """

    def __init__(self):
        """Initialize with no events and every counter at zero."""
        self.events: list[Event] = []
        self.total_packages = 0
        self.sorted_packages = 0
        self.rejected_packages = 0
        self.unknown_codes = 0
        self.scan_errors = 0
        self.gate_errors = 0
        self._timings: dict[str, _PackageTiming] = {}

    def record_package_created(self, timestamp: float, package_id: str) -> None:
        """Record a new package entering the system.

        Args:
            timestamp: Simulated time of the event, in seconds.
            package_id: Identifier of the package.
        """
        self.total_packages += 1
        self._timings[package_id] = _PackageTiming(created_at=timestamp)
        self.events.append(Event(timestamp, "PACKAGE_CREATED", package_id))

    def record_scan_error(self, timestamp: float, package_id: str) -> None:
        """Record a failed scan (CODE_NOT_FOUND, see README section 25).

        Args:
            timestamp: Simulated time of the event, in seconds.
            package_id: Identifier of the package.
        """
        self.scan_errors += 1
        self.events.append(Event(timestamp, "CODE_NOT_FOUND", package_id))

    def record_code_detected(self, timestamp: float, package_id: str, code: str) -> None:
        """Record a successful scan and mark the package's scan time.

        Args:
            timestamp: Simulated time of the event, in seconds.
            package_id: Identifier of the package.
            code: The decoded barcode.
        """
        timing = self._timings.get(package_id)
        if timing is not None:
            timing.scanned_at = timestamp
        self.events.append(Event(timestamp, "CODE_DETECTED", package_id, detail=code))

    def record_unknown_code(self, timestamp: float, package_id: str, code: str) -> None:
        """Record a successfully read but unroutable barcode (see README section 25).

        Args:
            timestamp: Simulated time of the event, in seconds.
            package_id: Identifier of the package.
            code: The decoded, unroutable barcode.
        """
        self.unknown_codes += 1
        self.rejected_packages += 1
        self.events.append(Event(timestamp, "UNKNOWN_BARCODE", package_id, detail=code))

    def record_gate_open(self, timestamp: float, package_id: str, gate_id: int) -> None:
        """Record a gate being triggered open for a package.

        Args:
            timestamp: Simulated time of the event, in seconds.
            package_id: Identifier of the package that triggered it.
            gate_id: Identifier of the gate.
        """
        self.events.append(Event(timestamp, "GATE_OPEN", package_id, detail=f"GATE-{gate_id}"))

    def record_gate_error(self, timestamp: float, package_id: str, gate_id: int) -> None:
        """Record a gate failing to open for a package (see README section 25).

        Args:
            timestamp: Simulated time of the event, in seconds.
            package_id: Identifier of the package that was stopped by it.
            gate_id: Identifier of the gate.
        """
        self.gate_errors += 1
        self.events.append(Event(timestamp, "GATE_ERROR", package_id, detail=f"GATE-{gate_id}"))

    def record_package_sorted(self, timestamp: float, package_id: str, gate_id: int) -> None:
        """Record a package reaching SORTED and mark its sort time.

        Args:
            timestamp: Simulated time of the event, in seconds.
            package_id: Identifier of the package.
            gate_id: Identifier of the gate it was routed through.
        """
        self.sorted_packages += 1
        timing = self._timings.get(package_id)
        if timing is not None:
            timing.sorted_at = timestamp
        self.events.append(Event(timestamp, "PACKAGE_SORTED", package_id, detail=f"GATE-{gate_id}"))

    @property
    def average_scan_time(self) -> float | None:
        """Average time from creation to a successful scan, in seconds.

        Returns:
            The average, or None if no package has been scanned yet.
        """
        durations = [t.scanned_at - t.created_at for t in self._timings.values() if t.scanned_at is not None]
        return sum(durations) / len(durations) if durations else None

    @property
    def average_sort_time(self) -> float | None:
        """Average time from creation to SORTED, in seconds.

        Returns:
            The average, or None if no package has been sorted yet.
        """
        durations = [t.sorted_at - t.created_at for t in self._timings.values() if t.sorted_at is not None]
        return sum(durations) / len(durations) if durations else None

    def summary(self, elapsed_time: float) -> dict:
        """Build the aggregate statistics summary (see README section 34).

        Args:
            elapsed_time: Simulated time elapsed since the run started, in
                seconds, used to derive throughput/packages_per_second.

        Returns:
            A dict with every counter and derived metric from section 34.
        """
        error_packages = self.scan_errors + self.gate_errors
        return {
            "total_packages": self.total_packages,
            "sorted_packages": self.sorted_packages,
            "rejected_packages": self.rejected_packages,
            "unknown_codes": self.unknown_codes,
            "scan_errors": self.scan_errors,
            "gate_errors": self.gate_errors,
            "error_packages": error_packages,
            "average_scan_time": self.average_scan_time,
            "average_sort_time": self.average_sort_time,
            "throughput": self.sorted_packages / elapsed_time if elapsed_time > 0 else 0.0,
            "packages_per_second": self.total_packages / elapsed_time if elapsed_time > 0 else 0.0,
            "success_rate": self.sorted_packages / self.total_packages if self.total_packages > 0 else None,
        }
