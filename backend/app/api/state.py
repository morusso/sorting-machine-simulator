from app.controllers.controller import Controller
from app.devices.gates.simulated_gate import SimulatedGate
from app.domain.conveyor import DrivenConveyorSegment
from app.domain.package import Package
from app.domain.scanner import ScanEvent, ScanResult
from app.simulation.clock import Clock
from app.simulation.engine import SimulationEngine

GATE_POSITIONS: dict[int, float] = {1: 7.0, 2: 9.0, 3: 11.0}
"""Gate positions along the conveyor, in meters (see README section 32)."""

GATE_OPEN_TIME_MS = 300.0
GATE_CLOSE_TIME_MS = 300.0

DEFAULT_ROUTING_TABLE: dict[str, int] = {
    "5901234567890": 1,
    "5900000000000": 2,
    "5911111111111": 3,
}
"""Placeholder barcode -> gate_id routing, standing in for a future
product/routing configuration endpoint (see README section 30)."""


class SimulationState:
    """Wires the engine, a conveyor segment, gates, and the controller
    together behind the REST/WebSocket API (see README sections 30-31).
    """

    def __init__(self):
        """Build a fresh simulation: one driven segment, 3 gates, engine STOPPED."""
        self.clock = Clock()
        self.engine = SimulationEngine(clock=self.clock)
        self.segment = DrivenConveyorSegment(length=20.0, speed=1.0, max_speed=2.0, acceleration=0.5)
        self.engine.add_segment(self.segment)

        self.gates: dict[int, SimulatedGate] = {
            gate_id: SimulatedGate(self.clock, open_time_ms=GATE_OPEN_TIME_MS, close_time_ms=GATE_CLOSE_TIME_MS)
            for gate_id in GATE_POSITIONS
        }
        approach_speed = self.segment.max_speed
        self.controller = Controller(
            gates=self.gates,
            gate_positions=GATE_POSITIONS,
            routing_table=dict(DEFAULT_ROUTING_TABLE),
            gate_lead_distances={gid: approach_speed * (GATE_OPEN_TIME_MS / 1000) for gid in GATE_POSITIONS},
            gate_clear_distances={gid: 0.5 for gid in GATE_POSITIONS},
        )
        self._package_count = 0

    async def create_package(self, barcode: str) -> Package:
        """Create a package with a known barcode and place it on the conveyor.

        Stands in for a full scanner pass: the barcode is applied
        immediately via handle_scan_result(), so the package is already
        SCANNED/ASSIGNED (or REJECTED, if unroutable) as soon as it enters
        the conveyor at position 0.

        Args:
            barcode: The package's barcode (see README section 30).

        Returns:
            The newly created package.
        """
        self._package_count += 1
        package_id = f"PKG-{self._package_count:06d}"
        package = Package(package_id=package_id, width=0.25, length=0.40, height=0.20)
        self.controller.register_package(package)
        self.segment.add_package(package_id, position=0.0)

        scan_result = ScanResult(
            event=ScanEvent.CODE_DETECTED,
            scan_id=f"SCAN-{self._package_count:06d}",
            package_id=package_id,
            code=barcode,
            position=0.0,
            confidence=1.0,
        )
        self.controller.handle_scan_result(scan_result)
        return package

    async def tick(self, real_dt: float) -> None:
        """Advance the engine and sync the controller's package positions.

        Args:
            real_dt: Elapsed real (wall-clock) time since the last tick,
                in seconds.
        """
        self.engine.tick(real_dt)
        await self.controller.sync_from_segments(self.engine.segments)

    async def snapshot(self) -> dict:
        """Build a WebSocket-ready snapshot of the current machine state.

        See README section 31 for the message shape.

        Returns:
            A dict with the conveyor speed, every tracked package's
            position/gate/status, and every gate's state.
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
        }

    def reset(self) -> None:
        """Reset the simulation to a fresh state: a new clock/engine, an
        empty conveyor, and a new gate set and controller (so no packages
        or gate state survive).
        """
        self.__init__()
