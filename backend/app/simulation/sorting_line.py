import random

from app.controllers.controller import Controller
from app.devices.gates.simulated_gate import SimulatedGate
from app.devices.scanner.simulated_scanner import SimulatedScanner
from app.domain.conveyor import DrivenConveyorSegment
from app.domain.package import Package, PackageStatus
from app.simulation.clock import Clock
from app.simulation.engine import SimulationEngine

DEFAULT_GATE_POSITIONS: dict[int, float] = {1: 7.0, 2: 9.0, 3: 11.0}
"""Gate positions along the conveyor, in meters (see README section 32)."""

GATE_OPEN_TIME_MS = 300.0
GATE_CLOSE_TIME_MS = 300.0

DEFAULT_SCANNER_POSITION = 2.0
"""Position of the scanner along the conveyor, in meters (see README
section 3: packages are scanned as they travel, ahead of the gates)."""

DEFAULT_ROUTING_TABLE: dict[str, int] = {
    "5901234567890": 1,
    "5900000000000": 2,
    "5911111111111": 3,
}
"""Placeholder barcode -> gate_id routing, standing in for a future
product/routing configuration endpoint (see README section 30)."""


class SortingLine:
    """Wires an engine, a driven conveyor segment, gates, a scanner, and a
    controller into one runnable sorting line.

    Used both by the REST/WebSocket API (see README sections 30-31) and by
    predefined test scenarios (see app/simulation/scenarios.py and README
    section 22), which is why every physical parameter is configurable
    rather than hardcoded to the API's defaults.
    """

    def __init__(
        self,
        segment_length: float = 20.0,
        segment_speed: float = 1.0,
        segment_max_speed: float = 2.0,
        segment_acceleration: float = 0.5,
        gate_positions: dict[int, float] | None = None,
        routing_table: dict[str, int] | None = None,
        scanner_error_rate: float = 0.0,
        scanner_position: float = DEFAULT_SCANNER_POSITION,
        rng: random.Random | None = None,
    ):
        """Build a fresh sorting line: one driven segment, gates, engine STOPPED.

        Args:
            segment_length: Length of the conveyor segment, in meters.
            segment_speed: Initial belt speed, in m/s.
            segment_max_speed: Maximum belt speed, in m/s.
            segment_acceleration: Belt acceleration/braking rate, in m/s^2.
            gate_positions: Position of each gate, in meters, keyed by
                gate_id. Defaults to DEFAULT_GATE_POSITIONS.
            routing_table: Maps a barcode to the gate_id it routes to.
                Defaults to DEFAULT_ROUTING_TABLE.
            scanner_error_rate: Probability, in [0, 1], that a scan fails
                to find a code (see README section 7).
            scanner_position: Position of the scanner along the conveyor,
                in meters.
            rng: Random source for the scanner's simulated error rate.
                Inject a seeded random.Random for deterministic scenarios.
        """
        self._config = dict(
            segment_length=segment_length,
            segment_speed=segment_speed,
            segment_max_speed=segment_max_speed,
            segment_acceleration=segment_acceleration,
            gate_positions=gate_positions,
            routing_table=routing_table,
            scanner_error_rate=scanner_error_rate,
            scanner_position=scanner_position,
            rng=rng,
        )
        gate_positions = dict(gate_positions) if gate_positions is not None else dict(DEFAULT_GATE_POSITIONS)
        routing_table = dict(routing_table) if routing_table is not None else dict(DEFAULT_ROUTING_TABLE)

        self.clock = Clock()
        self.engine = SimulationEngine(clock=self.clock)
        self.segment = DrivenConveyorSegment(
            length=segment_length,
            speed=segment_speed,
            max_speed=segment_max_speed,
            acceleration=segment_acceleration,
        )
        self.engine.add_segment(self.segment)

        self.gate_positions = gate_positions
        self.gates: dict[int, SimulatedGate] = {
            gate_id: SimulatedGate(self.clock, open_time_ms=GATE_OPEN_TIME_MS, close_time_ms=GATE_CLOSE_TIME_MS)
            for gate_id in gate_positions
        }
        self.controller = Controller(
            gates=self.gates,
            gate_positions=gate_positions,
            routing_table=routing_table,
            gate_lead_distances={gid: segment_max_speed * (GATE_OPEN_TIME_MS / 1000) for gid in gate_positions},
            gate_clear_distances={gid: 0.5 for gid in gate_positions},
            clock=self.clock,
        )
        self.scanner_position = scanner_position
        self.scanner = SimulatedScanner(error_rate=scanner_error_rate, rng=rng)
        self._unscanned_barcodes: dict[str, str] = {}
        self._package_count = 0

    async def create_package(self, barcode: str, position: float = 0.0) -> Package:
        """Create a package carrying the given barcode and place it on the conveyor.

        The barcode is only revealed once the package physically reaches
        scanner_position (see _scan_arrived_packages()), like a real
        scanner would — not applied instantly at creation.

        Args:
            barcode: The package's actual barcode (see README section 30).
            position: Initial position along the conveyor, in meters.

        Returns:
            The newly created package, initially IN_TRANSIT with no
            barcode/destination assigned yet.
        """
        self._package_count += 1
        package_id = f"PKG-{self._package_count:06d}"
        package = Package(package_id=package_id, width=0.25, length=0.40, height=0.20)
        package.status = PackageStatus.IN_TRANSIT
        self.controller.register_package(package)
        self.segment.add_package(package_id, position=position)
        self._unscanned_barcodes[package_id] = barcode
        return package

    async def _scan_arrived_packages(self) -> None:
        """Scan every package that has reached the scanner and apply the result.

        Mirrors the SimulatedScanner docstring's expectation that
        something with visibility into package positions calls enqueue()
        as packages reach the scanner's location, then reads the result
        back via scan() (see README sections 6-7).
        """
        for package_id in await self.segment.get_package_ids():
            barcode = self._unscanned_barcodes.get(package_id)
            if barcode is None:
                continue
            position = await self.segment.get_package_position(package_id)
            if position < self.scanner_position:
                continue
            del self._unscanned_barcodes[package_id]
            self.scanner.enqueue(package_id, barcode, position)
            result = await self.scanner.scan()
            self.controller.handle_scan_result(result)

    async def tick(self, real_dt: float) -> None:
        """Advance the engine, scan arrived packages, and sync the controller.

        Args:
            real_dt: Elapsed real (wall-clock) time since the last tick,
                in seconds.
        """
        self.engine.tick(real_dt)
        await self._scan_arrived_packages()
        await self.controller.sync_from_segments(self.engine.segments)

    async def snapshot(self) -> dict:
        """Build a WebSocket-ready snapshot of the current machine state.

        See README sections 31 and 34 for the message/statistics shape.

        Returns:
            A dict with the conveyor speed, every tracked package's
            position/gate/status, every gate's state, and the aggregate
            statistics summary.
        """
        return {
            "type": "simulation_state",
            "timestamp": self.clock.now(),
            "conveyor": {"speed": self.segment.speed},
            "packages": [
                {
                    "id": package.package_id,
                    "position": package.position,
                    "gate": package.destination,
                    "status": package.status,
                }
                for package in self.controller.packages.values()
            ],
            "gates": [{"id": gate_id, "state": await gate.get_state()} for gate_id, gate in self.gates.items()],
            "statistics": self.controller.statistics.summary(self.clock.now()),
        }

    def reset(self) -> None:
        """Reset the sorting line to a fresh state, preserving its original
        configuration: a new clock/engine, an empty conveyor, and a new
        gate set and controller (so no packages or gate state survive).
        """
        self.__init__(**self._config)
