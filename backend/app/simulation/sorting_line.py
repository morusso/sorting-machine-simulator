from app.controllers.controller import Controller
from app.devices.simulated_device_factory import SimulatedDeviceFactory
from app.domain.device_factory import DeviceFactory
from app.domain.gate import Gate
from app.domain.gravity_conveyor import GravityConveyorSegment
from app.domain.package import Package, PackageStatus
from app.simulation.clock import Clock
from app.simulation.engine import EngineState, SimulationEngine
from app.simulation.sorting_line_config import DEFAULT_SCANNER_POSITION, SortingLineConfig  # noqa: F401 (re-exported)

GATE_OPEN_TIME_MS = 300.0
GATE_CLOSE_TIME_MS = 300.0

ENTRY_SENSOR_ID = "SENSOR-ENTRY"
END_OF_BELT_SENSOR_ID = "SENSOR-END-OF-BELT"
ENTRY_SENSOR_RANGE_M = 0.1
"""How close to the segment's start a package must be to break the entry
sensor's beam, in meters (see README section 10)."""
END_OF_BELT_SENSOR_RANGE_M = 0.1
"""How close to the segment's end a package must be to break the
end-of-belt sensor's beam, in meters (see README section 10)."""

TERMINAL_PACKAGE_STATUSES = (PackageStatus.SORTED, PackageStatus.REJECTED, PackageStatus.ERROR, PackageStatus.LOST)
"""Statuses past which a package no longer needs anything done to it (see
_handoff_to_gravity_segment(), app.simulation.scenarios._is_settled())."""

GRAVITY_STALL_TIMEOUT_S = 2.0
"""How long a package must sit motionless on the gravity segment before
it's reported as GRAVITY_SEGMENT_STALL/_JAM (see README section 25,
_check_gravity_segment_faults())."""


class SortingLine:
    """Wires an engine, a driven conveyor segment, a downstream gravity
    buffer chain, gates, a scanner, and a controller into one runnable
    sorting line.

    Used both by the REST/WebSocket API (see README sections 30-31) and by
    predefined test scenarios (see app/simulation/scenarios.py and README
    section 22), which is why every physical parameter is configurable via
    SortingLineConfig rather than hardcoded to the API's defaults. Which
    concrete Gate/Scanner/segment classes get built is likewise
    configurable via a DeviceFactory (see app.domain.device_factory,
    Factory Method), defaulting to SimulatedDeviceFactory.

    The route is the driven segment followed by one or more gravity
    segments chained end to end (see README sections 4.1a and 32,
    `gravity_segments`): the driven segment carries packages past the
    scanner and gates, and any package that reaches its end (i.e. wasn't
    removed by a gate) is handed off onto the first segment in the gravity
    chain — a chute-style buffer with no gates of its own, driven purely
    by incline/friction/weight rather than belt speed — then on to each
    next segment in the chain as it clears the one before it (see
    _advance_gravity_chain()). The controller only ever sees the driven
    segment (see _handoff_to_gravity_segment()); the gravity chain needs
    no special casing anywhere in the routing/gate logic (see README
    section 28).
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
        self.engine.add_segment(self.segment)

        self.gravity_segments: dict[int, GravityConveyorSegment] = {}
        self._gravity_chain: list[int] = [
            spec.id for spec in sorted(config.gravity_segments, key=lambda spec: spec.position_start)
        ]
        for spec in config.gravity_segments:
            segment = self.device_factory.create_gravity_segment(
                length=spec.length,
                incline_angle=spec.incline_angle,
                friction_coefficient=spec.friction_coefficient,
                roller_diameter=spec.roller_diameter,
                min_package_weight=spec.min_package_weight,
            )
            self.gravity_segments[spec.id] = segment
            self.engine.add_segment(segment)

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
        self.scanner_detection_delay_s = config.scanner_detection_delay_ms / 1000
        self._unscanned_barcodes: dict[str, str] = {}
        self._pending_scans: dict[str, float] = {}
        self.scanner = self.device_factory.create_scanner(
            config.scanner_error_rate, config.rng, self._unscanned_barcodes.get
        )
        self.encoder = self.device_factory.create_encoder(self.segment)
        self.entry_sensor = self.device_factory.create_sensor(ENTRY_SENSOR_ID)
        self.end_of_belt_sensor = self.device_factory.create_sensor(END_OF_BELT_SENSOR_ID)
        self._package_count = 0
        self._entry_references: dict[str, tuple[int, float]] = {}
        self.emergency_stopped = False
        self._conveyor_fault_reported = False
        self._encoder_fault_reported = False
        self._reported_sensor_faults: set[str] = set()
        self._gravity_stall_timers: dict[str, float] = {}
        self._gravity_alerted: set[str] = set()

    @property
    def gravity_segment(self) -> GravityConveyorSegment:
        """The first segment in the gravity chain (see gravity_segments).

        A convenience accessor for the common single-segment
        configuration — a package leaving the driven segment always
        enters this one first (see _handoff_to_gravity_segment()).
        """
        return self.gravity_segments[self._gravity_chain[0]]

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
        self._entry_references[package_id] = (await self.encoder.get_pulse_count(), position)
        self._unscanned_barcodes[package_id] = barcode
        return package

    async def _scan_arrived_packages(self) -> None:
        """Trigger the scanner for newly-arrived packages, and resolve any
        whose read delay has elapsed.

        Detecting that a package has reached scanner_position is what a
        real photoelectric trigger would do (see README section 6); the
        scanner itself never needs to be told which package it's reading
        or what its "true" code is (see Scanner.scan()) — the true code is
        resolved via the barcode_lookup this line's scanner was
        constructed with (see SimulatedDeviceFactory.create_scanner()).
        The actual read is not applied the same instant a package crosses
        scanner_position: it's deferred by scanner_detection_delay_s, like
        a real scanner's decode latency (see README sections 7 and 32,
        "read delay"). A no-op while emergency_stopped is set (see README
        section 26, EMERGENCY_STOP: "Scanner | STOP / IDLE").
        """
        if self.emergency_stopped:
            return

        for package_id in await self.segment.get_package_ids():
            if package_id not in self._unscanned_barcodes or package_id in self._pending_scans:
                continue
            position = await self.segment.get_package_position(package_id)
            if position < self.scanner_position:
                continue
            self._pending_scans[package_id] = self.clock.now() + self.scanner_detection_delay_s

        now = self.clock.now()
        ready = [package_id for package_id, ready_at in self._pending_scans.items() if now >= ready_at]
        for package_id in ready:
            del self._pending_scans[package_id]
            position = await self.segment.get_package_position(package_id)
            result = await self.scanner.scan(package_id, position)
            del self._unscanned_barcodes[package_id]
            self.controller.handle_scan_result(result)

    async def _position_from_encoder(self, package_id: str) -> float:
        """Derive a driven-segment package's position from encoder pulses.

        Reconstructed as the package's entry position plus how far the
        belt has moved (per self.encoder.pulses_per_meter) since it
        entered, rather than read directly off DrivenConveyorSegment's own
        tracked position. This is what makes the encoder swappable without
        touching the sorting algorithm (see README sections 9, 14, 37):
        everything downstream only ever sees this derived value.

        Args:
            package_id: Identifier of the package to locate.

        Returns:
            The package's encoder-derived position, in meters, clamped to
            the segment length like DrivenConveyorSegment's own tracking.
        """
        entry_pulses, entry_position = self._entry_references[package_id]
        current_pulses = await self.encoder.get_pulse_count()
        distance_traveled = (current_pulses - entry_pulses) / self.encoder.pulses_per_meter
        return min(entry_position + distance_traveled, self.segment.length)

    async def _sync_controller_from_encoder(self) -> None:
        """Report every driven-segment package's encoder-derived position
        to the controller, triggering gates as usual.

        This is the only way a driven-segment package's position reaches
        the controller — never DrivenConveyorSegment's own tracked
        position directly (see _position_from_encoder()) — mirroring how a
        real controller only knows what its encoder reports, not the
        machine's "true" state (see README section 28).
        """
        for package_id in await self.segment.get_package_ids():
            if package_id not in self.controller.packages:
                continue
            position = await self._position_from_encoder(package_id)
            await self.controller.update_package_position(package_id, position)

    async def _update_sensors(self) -> None:
        """Trigger/clear the entry and end-of-belt sensors from current package positions.

        Sensors report the segment's actual physical state directly (like
        a real photoelectric beam would), independent of the encoder (see
        README section 10).
        """
        positions = [await self.segment.get_package_position(pid) for pid in await self.segment.get_package_ids()]

        if any(position <= ENTRY_SENSOR_RANGE_M for position in positions):
            self.entry_sensor.trigger()
        else:
            self.entry_sensor.clear()

        if any(position >= self.segment.length - END_OF_BELT_SENSOR_RANGE_M for position in positions):
            self.end_of_belt_sensor.trigger()
        else:
            self.end_of_belt_sensor.clear()

    async def _handoff_to_gravity_segment(self) -> None:
        """Hand off packages that reached the end of the driven segment.

        A package that reaches the driven segment's end without having
        been removed by a gate (i.e. it's SORTED-but-not-yet-clear,
        REJECTED, or ERROR — see Controller) rolls off onto the gravity
        segment instead of piling up at the belt's end forever. Entry
        velocity carries over from the belt's current speed (see README
        section 4.1a: exit speed depends on entry speed); weight comes
        from the package's own record.

        A package that reaches the end while still in a non-terminal
        status (e.g. it overran its destination gate in one large position
        jump, see Controller.update_package_position()) is marked
        PACKAGE_LOST instead (see README section 25) before being handed
        off the same way — the controller has no gates on the gravity
        segment to route it with any more, so tracking it as anything but
        lost would be misleading.
        """
        for package_id in await self.segment.get_package_ids():
            position = await self.segment.get_package_position(package_id)
            if position < self.segment.length:
                continue
            package = self.controller.packages[package_id]
            if package.status not in TERMINAL_PACKAGE_STATUSES:
                self.controller.mark_lost(package_id)
            self.segment.remove_package(package_id)
            del self._entry_references[package_id]
            self._unscanned_barcodes.pop(package_id, None)
            self._pending_scans.pop(package_id, None)
            self.gravity_segment.add_package(
                package_id, weight=package.weight, position=0.0, velocity=self.segment.speed
            )

    def _check_device_faults(self) -> None:
        """Report any newly-faulted device once (CONVEYOR_STOPPED, SENSOR_ERROR, ENCODER_ERROR).

        Fault injection itself happens elsewhere (e.g.
        DrivenConveyorSegment.simulate_fault(), SimulatedSensor.
        simulate_error(), SimulatedEncoder.simulate_error()) — this only
        turns a device's faulted flag into a one-shot logged event/
        statistic the first tick it's observed (see README section 25).
        """
        if self.segment.faulted and not self._conveyor_fault_reported:
            self._conveyor_fault_reported = True
            self.controller.record_conveyor_stopped()

        if self.encoder.faulted and not self._encoder_fault_reported:
            self._encoder_fault_reported = True
            self.controller.record_encoder_error()

        for sensor in (self.entry_sensor, self.end_of_belt_sensor):
            if sensor.faulted and sensor.sensor_id not in self._reported_sensor_faults:
                self._reported_sensor_faults.add(sensor.sensor_id)
                self.controller.record_sensor_error(sensor.sensor_id)

    async def _advance_gravity_chain(self) -> None:
        """Hand packages off between consecutive segments in the gravity chain.

        A package that reaches the end of a gravity segment that isn't
        the last one in gravity_segments moves on to the next segment in
        chain order, carrying over its velocity (see README section 4.1a:
        exit speed depends on entry speed) — the same handoff
        _handoff_to_gravity_segment() does from the driven segment, one
        level down. A package on the last segment in the chain just stays
        there once it clears it; there's nothing further to hand off to.
        """
        for current_id, next_id in zip(self._gravity_chain, self._gravity_chain[1:]):
            current = self.gravity_segments[current_id]
            next_segment = self.gravity_segments[next_id]
            for package_id in await current.get_package_ids():
                position = await current.get_package_position(package_id)
                if position < current.length:
                    continue
                velocity = await current.get_package_velocity(package_id)
                weight = self.controller.packages[package_id].weight
                current.remove_package(package_id)
                next_segment.add_package(package_id, weight=weight, position=0.0, velocity=velocity)

    async def _check_gravity_segment_faults(self, dt: float) -> None:
        """Detect packages stalling/piling up anywhere in the gravity chain.

        A package with zero velocity that hasn't yet cleared the segment
        it's on is timed; once it's been motionless for
        GRAVITY_STALL_TIMEOUT_S, it's reported once as GRAVITY_SEGMENT_JAM
        if it's resting against another stopped package ahead of it (a
        pile-up, see GravityConveyorSegment.advance()'s overtake
        prevention), or GRAVITY_SEGMENT_STALL otherwise (stopped on its
        own, e.g. too light for that segment's incline/friction, see
        README section 25).

        Args:
            dt: Elapsed simulated time since the last check, in seconds.
        """
        all_package_ids: set[str] = set()

        for segment_id in self._gravity_chain:
            segment = self.gravity_segments[segment_id]
            package_ids = await segment.get_package_ids()
            all_package_ids.update(package_ids)
            positions = {pid: await segment.get_package_position(pid) for pid in package_ids}
            velocities = {pid: await segment.get_package_velocity(pid) for pid in package_ids}
            ordered = sorted(package_ids, key=lambda pid: -positions[pid])

            for index, package_id in enumerate(ordered):
                if velocities[package_id] != 0.0 or positions[package_id] >= segment.length:
                    self._gravity_stall_timers.pop(package_id, None)
                    self._gravity_alerted.discard(package_id)
                    continue

                self._gravity_stall_timers[package_id] = self._gravity_stall_timers.get(package_id, 0.0) + dt
                if package_id in self._gravity_alerted:
                    continue
                if self._gravity_stall_timers[package_id] < GRAVITY_STALL_TIMEOUT_S:
                    continue

                self._gravity_alerted.add(package_id)
                blocked_by_package_ahead = index > 0 and positions[package_id] == positions[ordered[index - 1]]
                if blocked_by_package_ahead:
                    self.controller.record_gravity_jam(package_id)
                else:
                    self.controller.record_gravity_stall(package_id)

        for stale in set(self._gravity_stall_timers) - all_package_ids:
            del self._gravity_stall_timers[stale]
            self._gravity_alerted.discard(stale)

    async def tick(self, real_dt: float) -> None:
        """Advance the engine, scan arrived packages, sync the controller,
        hand off packages that reached the end of the driven segment, and
        report any device faults or gravity-segment stalls/jams.

        Args:
            real_dt: Elapsed real (wall-clock) time since the last tick,
                in seconds.
        """
        sim_dt = self.engine.tick(real_dt)
        await self._scan_arrived_packages()
        await self._update_sensors()
        await self._sync_controller_from_encoder()
        await self._handoff_to_gravity_segment()
        await self._advance_gravity_chain()
        self._check_device_faults()
        await self._check_gravity_segment_faults(sim_dt)

    async def emergency_stop(self) -> None:
        """Trip the emergency stop (see README section 26).

        Reacts exactly as the safety table there specifies: stops the
        driven conveyor outright, engages every gravity segment's
        mechanical stopper (none of them have a motor to disable), forces
        every gate to SAFE_STATE, idles the scanner, and puts the
        controller into SAFE_MODE.

        Always succeeds, regardless of the current engine/gate/controller
        state — an emergency stop must never be refused. There is no
        partial "un-emergency-stop": recovery requires a full reset() (see
        SortingLine.reset()).
        """
        if self.engine.state != EngineState.STOPPED:
            self.engine.stop()
        self.segment.emergency_stop()
        for gravity_segment in self.gravity_segments.values():
            gravity_segment.engage_stopper()
        for gate in self.gates.values():
            await gate.emergency_stop()
        self.emergency_stopped = True
        self.controller.enter_safe_mode()

    async def snapshot(self) -> dict:
        """Build a WebSocket-ready snapshot of the current machine state.

        See README sections 31 and 34 for the message/statistics shape.

        Returns:
            A dict with the engine's lifecycle state, the conveyor's
            speed/length, every tracked package's position/gate/status/eta
            (see Controller.estimate_gate_eta()), every gate's
            position/state, each gravity segment's packages in chain
            order, and the aggregate statistics summary.
        """
        return {
            "type": "simulation_state",
            "timestamp": self.clock.now(),
            "engine_state": self.engine.state,
            "speed_multiplier": self.clock.speed_multiplier,
            "emergency_stopped": self.emergency_stopped,
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
                    "eta": self.controller.estimate_gate_eta(package.package_id, self.segment.speed),
                }
                for package in self.controller.packages.values()
            ],
            "gates": [
                {"id": gate_id, "position": self.gate_positions[gate_id], "state": await gate.get_state()}
                for gate_id, gate in self.gates.items()
            ],
            "encoder": {"pulse_count": await self.encoder.get_pulse_count()},
            "sensors": [
                {"id": ENTRY_SENSOR_ID, "triggered": await self.entry_sensor.is_triggered()},
                {"id": END_OF_BELT_SENSOR_ID, "triggered": await self.end_of_belt_sensor.is_triggered()},
            ],
            "gravity_segments": [
                {
                    "id": segment_id,
                    "length": self.gravity_segments[segment_id].length,
                    "packages": [
                        {
                            "id": package_id,
                            "position": await self.gravity_segments[segment_id].get_package_position(package_id),
                            "velocity": await self.gravity_segments[segment_id].get_package_velocity(package_id),
                        }
                        for package_id in await self.gravity_segments[segment_id].get_package_ids()
                    ],
                }
                for segment_id in self._gravity_chain
            ],
            "statistics": self.controller.statistics.summary(self.clock.now()),
        }

    def reset(self) -> None:
        """Reset the sorting line to a fresh state, preserving its original
        configuration: a new clock/engine, an empty conveyor, and a new
        gate set and controller (so no packages or gate state survive).
        """
        self.__init__(config=self.config, device_factory=self.device_factory)
