import random

from app.controllers.controller import Controller
from app.devices.gates.simulated_gate import SimulatedGate
from app.devices.scanner.simulated_scanner import SimulatedScanner
from app.domain.conveyor import DrivenConveyorSegment
from app.domain.gravity_conveyor import GravityConveyorSegment
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

DEFAULT_GRAVITY_LENGTH = 3.0
DEFAULT_GRAVITY_INCLINE_ANGLE = 8.0
DEFAULT_GRAVITY_FRICTION_COEFFICIENT = 0.04
DEFAULT_GRAVITY_ROLLER_DIAMETER = 0.05
DEFAULT_GRAVITY_MIN_PACKAGE_WEIGHT = 0.2
"""Defaults for the gravity buffer segment past the end of the driven
segment, matching the example machine configuration in README section 32
and the parameter table in section 4.1a."""


class SortingLine:
    """Wires an engine, a driven conveyor segment, a downstream gravity
    buffer segment, gates, a scanner, and a controller into one runnable
    sorting line.

    Used both by the REST/WebSocket API (see README sections 30-31) and by
    predefined test scenarios (see app/simulation/scenarios.py and README
    section 22), which is why every physical parameter is configurable
    rather than hardcoded to the API's defaults.

    The route is two segments end to end (see README section 4.1a): the
    driven segment carries packages past the scanner and gates, and any
    package that reaches its end (i.e. wasn't removed by a gate) is handed
    off onto the gravity segment — a chute-style buffer with no gates of
    its own, driven purely by incline/friction/weight rather than belt
    speed. The controller only ever sees the driven segment (see
    _handoff_to_gravity_segment()); the gravity segment needs no special
    casing anywhere in the routing/gate logic (see README section 28).
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
        gravity_length: float = DEFAULT_GRAVITY_LENGTH,
        gravity_incline_angle: float = DEFAULT_GRAVITY_INCLINE_ANGLE,
        gravity_friction_coefficient: float = DEFAULT_GRAVITY_FRICTION_COEFFICIENT,
        gravity_roller_diameter: float = DEFAULT_GRAVITY_ROLLER_DIAMETER,
        gravity_min_package_weight: float = DEFAULT_GRAVITY_MIN_PACKAGE_WEIGHT,
        rng: random.Random | None = None,
    ):
        """Build a fresh sorting line: driven + gravity segments, gates, engine STOPPED.

        Args:
            segment_length: Length of the driven conveyor segment, in
                meters.
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
            gravity_length: Length of the downstream gravity buffer
                segment, in meters.
            gravity_incline_angle: Incline angle of the gravity segment, in
                degrees (positive = downhill).
            gravity_friction_coefficient: Rolling/sliding friction
                coefficient of the gravity segment.
            gravity_roller_diameter: Roller diameter of the gravity
                segment, in meters.
            gravity_min_package_weight: Minimum package mass, in kg, below
                which a package won't move on the gravity segment.
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
            gravity_length=gravity_length,
            gravity_incline_angle=gravity_incline_angle,
            gravity_friction_coefficient=gravity_friction_coefficient,
            gravity_roller_diameter=gravity_roller_diameter,
            gravity_min_package_weight=gravity_min_package_weight,
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
        self.gravity_segment = GravityConveyorSegment(
            length=gravity_length,
            incline_angle=gravity_incline_angle,
            friction_coefficient=gravity_friction_coefficient,
            roller_diameter=gravity_roller_diameter,
            min_package_weight=gravity_min_package_weight,
        )
        self.engine.add_segment(self.segment)
        self.engine.add_segment(self.gravity_segment)

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
        self.events = self.controller.events
        self.scanner_position = scanner_position
        self.scanner = SimulatedScanner(error_rate=scanner_error_rate, rng=rng)
        self._unscanned_barcodes: dict[str, str] = {}
        self._package_count = 0

    async def create_package(self, barcode: str, position: float = 0.0, weight: float = 1.0) -> Package:
        """Create a package carrying the given barcode and place it on the conveyor.

        The barcode is only revealed once the package physically reaches
        scanner_position (see _scan_arrived_packages()), like a real
        scanner would — not applied instantly at creation.

        Args:
            barcode: The package's actual barcode (see README section 30).
            position: Initial position along the conveyor, in meters.
            weight: Package mass, in kg. Irrelevant on the driven segment,
                but determines how the package behaves once handed off to
                the gravity segment (see _handoff_to_gravity_segment()).

        Returns:
            The newly created package, initially IN_TRANSIT with no
            barcode/destination assigned yet.
        """
        self._package_count += 1
        package_id = f"PKG-{self._package_count:06d}"
        package = Package(package_id=package_id, width=0.25, length=0.40, height=0.20, weight=weight)
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

    async def _handoff_to_gravity_segment(self) -> None:
        """Hand off packages that reached the end of the driven segment.

        A package that reaches the driven segment's end without having
        been removed by a gate (i.e. it's SORTED-but-not-yet-clear,
        REJECTED, or ERROR — see Controller) rolls off onto the gravity
        segment instead of piling up at the belt's end forever. Entry
        velocity carries over from the belt's current speed (see README
        section 4.1a: exit speed depends on entry speed); weight comes
        from the package's own record.
        """
        for package_id in await self.segment.get_package_ids():
            position = await self.segment.get_package_position(package_id)
            if position < self.segment.length:
                continue
            package = self.controller.packages[package_id]
            self.segment.remove_package(package_id)
            self.gravity_segment.add_package(
                package_id, weight=package.weight, position=0.0, velocity=self.segment.speed
            )

    async def tick(self, real_dt: float) -> None:
        """Advance the engine, scan arrived packages, sync the controller,
        and hand off packages that reached the end of the driven segment.

        Args:
            real_dt: Elapsed real (wall-clock) time since the last tick,
                in seconds.
        """
        self.engine.tick(real_dt)
        await self._scan_arrived_packages()
        await self.controller.sync_from_segments([self.segment])
        await self._handoff_to_gravity_segment()

    async def snapshot(self) -> dict:
        """Build a WebSocket-ready snapshot of the current machine state.

        See README sections 31 and 34 for the message/statistics shape.

        Returns:
            A dict with the engine's lifecycle state, the conveyor's
            speed/length, every tracked package's position/gate/status,
            every gate's position/state, the gravity buffer's packages,
            and the aggregate statistics summary.
        """
        return {
            "type": "simulation_state",
            "timestamp": self.clock.now(),
            "engine_state": self.engine.state,
            "conveyor": {
                "speed": self.segment.speed,
                "target_speed": self.segment.target_speed,
                "length": self.segment.length,
            },
            "packages": [
                {
                    "id": package.package_id,
                    "position": package.position,
                    "gate": package.destination,
                    "status": package.status,
                }
                for package in self.controller.packages.values()
            ],
            "gates": [
                {"id": gate_id, "position": self.gate_positions[gate_id], "state": await gate.get_state()}
                for gate_id, gate in self.gates.items()
            ],
            "gravity_segment": {
                "length": self.gravity_segment.length,
                "packages": [
                    {
                        "id": package_id,
                        "position": await self.gravity_segment.get_package_position(package_id),
                        "velocity": await self.gravity_segment.get_package_velocity(package_id),
                    }
                    for package_id in await self.gravity_segment.get_package_ids()
                ],
            },
            "statistics": self.controller.statistics.summary(self.clock.now()),
        }

    def reset(self) -> None:
        """Reset the sorting line to a fresh state, preserving its original
        configuration: a new clock/engine, an empty conveyor, and a new
        gate set and controller (so no packages or gate state survive).
        """
        self.__init__(**self._config)
