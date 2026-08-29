from app.controllers.controller import Controller
from app.devices.simulated_device_factory import SimulatedDeviceFactory
from app.domain.device_factory import DeviceFactory
from app.domain.gate import Gate
from app.domain.package import Package, PackageStatus
from app.simulation.clock import Clock
from app.simulation.engine import SimulationEngine
from app.simulation.sorting_line_config import DEFAULT_SCANNER_POSITION, SortingLineConfig  # noqa: F401 (re-exported)

GATE_OPEN_TIME_MS = 300.0
GATE_CLOSE_TIME_MS = 300.0


class SortingLine:
    """Wires an engine, a driven conveyor segment, a downstream gravity
    buffer segment, gates, a scanner, and a controller into one runnable
    sorting line.

    Used both by the REST/WebSocket API (see README sections 30-31) and by
    predefined test scenarios (see app/simulation/scenarios.py and README
    section 22), which is why every physical parameter is configurable via
    SortingLineConfig rather than hardcoded to the API's defaults. Which
    concrete Gate/Scanner/segment classes get built is likewise
    configurable via a DeviceFactory (see app.domain.device_factory,
    Factory Method), defaulting to SimulatedDeviceFactory.

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
        config: SortingLineConfig | None = None,
        device_factory: DeviceFactory | None = None,
    ):
        """Build a fresh sorting line: driven + gravity segments, gates, engine STOPPED.

        Args:
            config: Physical layout — segment/gravity-segment geometry,
                gate positions, routing, scanner behavior (see
                SortingLineConfig). Defaults to a fresh SortingLineConfig()
                if not given.
            device_factory: Builds the driven/gravity segments, gates, and
                scanner this line drives (see app.domain.device_factory,
                Factory Method). Defaults to a fresh SimulatedDeviceFactory()
                if not given — inject a factory backed by real hardware
                (see README section 28) to drive real equipment without
                changing this class.
        """
        self.config = config if config is not None else SortingLineConfig()
        self.device_factory = device_factory if device_factory is not None else SimulatedDeviceFactory()
        config = self.config

        self.clock = Clock()
        self.engine = SimulationEngine(clock=self.clock)
        self.segment = self.device_factory.create_driven_segment(
            length=config.segment_length,
            speed=config.segment_speed,
            max_speed=config.segment_max_speed,
            acceleration=config.segment_acceleration,
        )
        self.gravity_segment = self.device_factory.create_gravity_segment(
            length=config.gravity_length,
            incline_angle=config.gravity_incline_angle,
            friction_coefficient=config.gravity_friction_coefficient,
            roller_diameter=config.gravity_roller_diameter,
            min_package_weight=config.gravity_min_package_weight,
        )
        self.engine.add_segment(self.segment)
        self.engine.add_segment(self.gravity_segment)

        self.gate_positions = config.gate_positions
        self.gates: dict[int, Gate] = {
            gate_id: self.device_factory.create_gate(self.clock, GATE_OPEN_TIME_MS, GATE_CLOSE_TIME_MS)
            for gate_id in config.gate_positions
        }
        self.controller = Controller(
            gates=self.gates,
            gate_positions=config.gate_positions,
            routing_table=config.routing_table,
            gate_lead_distances={
                gid: config.segment_max_speed * (GATE_OPEN_TIME_MS / 1000) for gid in config.gate_positions
            },
            gate_clear_distances={gid: 0.5 for gid in config.gate_positions},
            clock=self.clock,
        )
        self.events = self.controller.events
        self.scanner_position = config.scanner_position
        self.scanner = self.device_factory.create_scanner(config.scanner_error_rate, config.rng)
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
        self.__init__(config=self.config, device_factory=self.device_factory)
