from app.domain.conveyor import ConveyorSegment
from app.domain.gate import Gate
from app.domain.package import Package, PackageStatus
from app.domain.scanner import ScanEvent, ScanResult
from app.simulation.clock import Clock
from app.simulation.statistics import Statistics


class Controller:
    """Central controller: identification, routing, and gate triggering.

    See README section 12. The controller does not know whether the
    scanner, gates, or transport segments it drives are simulated or real
    (see section 28) — it only depends on the Scanner/Gate/ConveyorSegment
    interfaces and the package positions reported to it.

    Attributes:
        gates: Gate actuators, keyed by gate_id.
        gate_positions: Position of each gate along the transport axis, in
            meters, keyed by gate_id.
        routing_table: Maps a decoded barcode to the gate_id it should be
            routed to. A barcode with no entry is treated as unroutable
            (see README section 25, UNKNOWN_BARCODE).
        gate_lead_distances: How far before a gate's position (in meters)
            the controller must trigger open() for it to have finished
            opening by the time the package arrives, keyed by gate_id.
            Computed by the caller from each gate's open_time_ms and the
            expected approach speed (see README section 14).
        gate_clear_distances: How far past a gate's position (in meters) a
            sorted package must travel before the controller closes the
            gate behind it, keyed by gate_id.
        clock: Simulation clock, used to timestamp events recorded in
            statistics (see README sections 24, 34).
        statistics: Event log and aggregate counters, updated as packages
            move through the system.
    """

    def __init__(
        self,
        gates: dict[int, Gate],
        gate_positions: dict[int, float],
        routing_table: dict[str, int],
        gate_lead_distances: dict[int, float],
        gate_clear_distances: dict[int, float],
        clock: Clock,
        statistics: Statistics | None = None,
    ):
        """Initialize the controller with static routing/gate configuration.

        Args:
            gates: Gate actuators, keyed by gate_id.
            gate_positions: Position of each gate along the transport axis,
                in meters, keyed by gate_id.
            routing_table: Maps a decoded barcode to the gate_id it should
                be routed to.
            gate_lead_distances: Distance before each gate's position, in
                meters, at which to trigger it open, keyed by gate_id.
            gate_clear_distances: Distance past each gate's position, in
                meters, at which to close it again, keyed by gate_id.
            clock: Simulation clock to timestamp recorded events with.
            statistics: Event log/counters to record into. Defaults to a
                fresh Statistics() if not given.
        """
        self.gates = gates
        self.gate_positions = gate_positions
        self.routing_table = routing_table
        self.gate_lead_distances = gate_lead_distances
        self.gate_clear_distances = gate_clear_distances
        self.clock = clock
        self.statistics = statistics if statistics is not None else Statistics()
        self.packages: dict[str, Package] = {}
        self._closing_packages: dict[int, str] = {}

    def register_package(self, package: Package) -> None:
        """Start tracking a package as it enters the system.

        Args:
            package: The package to track, keyed internally by its
                package_id.
        """
        self.packages[package.package_id] = package
        self.statistics.record_package_created(self.clock.now(), package.package_id)

    def handle_scan_result(self, result: ScanResult) -> Package:
        """Apply a scan outcome to the corresponding tracked package.

        A CODE_NOT_FOUND result marks the package ERROR (see README
        section 25). A CODE_DETECTED result records the barcode and either
        assigns a destination gate from routing_table (status ASSIGNED) or,
        if the barcode has no routing entry, marks the package REJECTED
        (UNKNOWN_BARCODE).

        Args:
            result: The scan outcome to apply.

        Returns:
            The updated package.

        Raises:
            KeyError: If result.package_id is not a tracked package.
        """
        package = self.packages[result.package_id]
        now = self.clock.now()

        if result.event == ScanEvent.CODE_NOT_FOUND:
            package.status = PackageStatus.ERROR
            self.statistics.record_scan_error(now, result.package_id)
            return package

        package.barcode = result.code
        package.status = PackageStatus.SCANNED
        self.statistics.record_code_detected(now, result.package_id, result.code)

        gate_id = self.routing_table.get(result.code)
        if gate_id is None:
            package.status = PackageStatus.REJECTED
            self.statistics.record_unknown_code(now, result.package_id, result.code)
            return package

        package.destination = gate_id
        package.status = PackageStatus.ASSIGNED
        return package

    @staticmethod
    def calculate_arrival_time(current_position: float, target_position: float, speed: float) -> float:
        """Estimate time to reach target_position at a constant speed.

        See README section 14: positioning should be based on measured
        position, not on timers alone — this is meant to be recalculated
        against the package's current position each time speed changes,
        rather than scheduled once and trusted.

        Args:
            current_position: Package's current position, in meters.
            target_position: Position to reach, in meters.
            speed: Package's current speed, in m/s.

        Returns:
            Estimated time to reach target_position, in seconds.

        Raises:
            ValueError: If target_position is behind current_position, or
                speed is not positive.
        """
        distance = target_position - current_position
        if distance < 0:
            raise ValueError("target_position must not be behind current_position")
        if speed <= 0:
            raise ValueError("speed must be positive to estimate arrival time")
        return distance / speed

    async def update_package_position(self, package_id: str, position: float) -> Package:
        """Report a package's current position and trigger its gate if due.

        For an ASSIGNED package, opens its destination gate once position
        reaches gate_lead_distances before the gate (moving the package to
        WAITING_FOR_GATE). For a WAITING_FOR_GATE package, marks it SORTED
        once position reaches the gate itself, and schedules the gate to
        close again once the package has cleared it by gate_clear_distances
        (see _close_gate_if_clear()).

        Args:
            package_id: Identifier of the package to update.
            position: The package's current position, in meters.

        Returns:
            The updated package.

        Raises:
            KeyError: If package_id is not a tracked package, or its
                destination gate_id is not a known gate.
        """
        package = self.packages[package_id]
        package.position = position

        await self._close_gate_if_clear(package_id, position)

        if package.status not in (PackageStatus.ASSIGNED, PackageStatus.WAITING_FOR_GATE):
            return package

        gate_id = package.destination
        gate_position = self.gate_positions[gate_id]

        if package.status == PackageStatus.ASSIGNED:
            trigger_position = gate_position - self.gate_lead_distances[gate_id]
            if position >= trigger_position:
                try:
                    await self.gates[gate_id].open()
                except RuntimeError:
                    # Gate not in a state that can open (e.g. stuck in
                    # ERROR, see README section 25, GATE_ERROR) — the
                    # package can't be routed, so it stops here instead.
                    package.status = PackageStatus.ERROR
                    self.statistics.record_gate_error(self.clock.now(), package_id, gate_id)
                else:
                    package.status = PackageStatus.WAITING_FOR_GATE
                    self.statistics.record_gate_open(self.clock.now(), package_id, gate_id)
        elif position >= gate_position:
            package.status = PackageStatus.SORTED
            self._closing_packages[gate_id] = package_id
            self.statistics.record_package_sorted(self.clock.now(), package_id, gate_id)

        return package

    async def _close_gate_if_clear(self, package_id: str, position: float) -> None:
        """Close a gate once the package that just went through it has cleared.

        Args:
            package_id: Identifier of the package whose position was just
                reported.
            position: The package's current position, in meters.
        """
        gate_id = self.packages[package_id].destination
        if gate_id is None or self._closing_packages.get(gate_id) != package_id:
            return

        close_trigger_position = self.gate_positions[gate_id] + self.gate_clear_distances[gate_id]
        if position >= close_trigger_position:
            await self.gates[gate_id].close()
            del self._closing_packages[gate_id]

    async def sync_from_segments(self, segments: list[ConveyorSegment]) -> None:
        """Poll transport segments and update every tracked package's position.

        Bridges the engine's physics (see SimulationEngine.tick(), which
        advances package positions on each registered segment) to the
        controller's routing/gate logic, without the engine needing to
        know about the controller (see README section 3: the engine owns
        motion, the controller owns decisions). Segments may be driven or
        gravity-based interchangeably (section 4.1a).

        Args:
            segments: Transport segments to poll for package positions.
                Packages not tracked by this controller are ignored.
        """
        for segment in segments:
            for package_id in await segment.get_package_ids():
                if package_id in self.packages:
                    position = await segment.get_package_position(package_id)
                    await self.update_package_position(package_id, position)
