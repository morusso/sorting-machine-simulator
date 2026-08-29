"""Concrete DeviceFactory building the simulated devices SortingLine uses today."""

import random

from app.devices.gates.simulated_gate import SimulatedGate
from app.devices.scanner.simulated_scanner import SimulatedScanner
from app.domain.conveyor import DrivenConveyorSegment
from app.domain.device_factory import DeviceFactory
from app.domain.gate import Gate
from app.domain.gravity_conveyor import GravityConveyorSegment
from app.domain.scanner import Scanner
from app.simulation.clock import Clock


class SimulatedDeviceFactory(DeviceFactory):
    """Builds DrivenConveyorSegment/GravityConveyorSegment/SimulatedGate/SimulatedScanner.

    The default DeviceFactory used by SortingLine. A future real-hardware
    factory (see README section 28) would implement the same interface,
    e.g. building gates/scanners that talk to a PLC or a TCP device
    instead of computing simulated physics/timers.
    """

    def create_driven_segment(
        self, length: float, speed: float, max_speed: float, acceleration: float
    ) -> DrivenConveyorSegment:
        """See DeviceFactory.create_driven_segment."""
        return DrivenConveyorSegment(length=length, speed=speed, max_speed=max_speed, acceleration=acceleration)

    def create_gravity_segment(
        self,
        length: float,
        incline_angle: float,
        friction_coefficient: float,
        roller_diameter: float,
        min_package_weight: float,
    ) -> GravityConveyorSegment:
        """See DeviceFactory.create_gravity_segment."""
        return GravityConveyorSegment(
            length=length,
            incline_angle=incline_angle,
            friction_coefficient=friction_coefficient,
            roller_diameter=roller_diameter,
            min_package_weight=min_package_weight,
        )

    def create_gate(self, clock: Clock, open_time_ms: float, close_time_ms: float) -> Gate:
        """See DeviceFactory.create_gate."""
        return SimulatedGate(clock, open_time_ms=open_time_ms, close_time_ms=close_time_ms)

    def create_scanner(self, error_rate: float, rng: random.Random | None) -> Scanner:
        """See DeviceFactory.create_scanner."""
        return SimulatedScanner(error_rate=error_rate, rng=rng)
