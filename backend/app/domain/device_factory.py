"""Factory Method interface for building the hardware a SortingLine drives.

SortingLine depends only on this interface — not on any concrete device
class such as SimulatedGate or SimulatedScanner — so a factory backed by
real hardware (see README section 28) can be swapped in without changing
SortingLine itself.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING

from app.domain.conveyor import DrivenConveyorSegment
from app.domain.encoder import Encoder
from app.domain.gate import Gate
from app.domain.gravity_conveyor import GravityConveyorSegment
from app.domain.scanner import Scanner
from app.domain.sensor import Sensor

if TYPE_CHECKING:
    # Only for type hints: app/domain must not depend on app/simulation at
    # runtime (Clock has no dependencies of its own, but the import
    # direction is kept one-way regardless).
    from app.simulation.clock import Clock


class DeviceFactory(ABC):
    """Builds the driven/gravity segments, gates, scanner, encoder, and
    sensors a SortingLine drives.
    """

    @abstractmethod
    def create_driven_segment(
        self, length: float, speed: float, max_speed: float, acceleration: float
    ) -> DrivenConveyorSegment:
        """Build the driven segment packages travel past the scanner and gates on.

        Args:
            length: Length of the segment, in meters.
            speed: Initial belt speed, in m/s.
            max_speed: Maximum belt speed, in m/s.
            acceleration: Belt acceleration/braking rate, in m/s^2.

        Returns:
            A driven conveyor segment.
        """
        raise NotImplementedError

    @abstractmethod
    def create_gravity_segment(
        self,
        length: float,
        incline_angle: float,
        friction_coefficient: float,
        roller_diameter: float,
        min_package_weight: float,
    ) -> GravityConveyorSegment:
        """Build the gravity buffer segment past the end of the driven segment.

        Args:
            length: Length of the segment, in meters.
            incline_angle: Incline angle, in degrees (positive = downhill).
            friction_coefficient: Rolling/sliding friction coefficient.
            roller_diameter: Roller diameter, in meters.
            min_package_weight: Minimum package mass, in kg, below which a
                package may not move.

        Returns:
            A gravity conveyor segment.
        """
        raise NotImplementedError

    @abstractmethod
    def create_gate(self, clock: Clock, open_time_ms: float, close_time_ms: float) -> Gate:
        """Build one sorting gate actuator.

        Args:
            clock: Simulation clock the gate times its transitions
                against.
            open_time_ms: Time to transition from CLOSED to OPEN, in
                milliseconds.
            close_time_ms: Time to transition from OPEN to CLOSED, in
                milliseconds.

        Returns:
            A gate actuator.
        """
        raise NotImplementedError

    @abstractmethod
    def create_scanner(
        self,
        error_rate: float,
        rng: random.Random | None,
        barcode_lookup: Callable[[str], str | None],
    ) -> Scanner:
        """Build the barcode scanner packages pass on their way to the gates.

        Args:
            error_rate: Probability, in [0, 1], that a scan attempt fails
                to find a code.
            rng: Random source used to decide scan outcomes.
            barcode_lookup: Given a package_id, returns that package's
                true barcode (or None if unknown). Simulation-only — a
                real scanner factory would ignore this, since a real
                scanner reads the code optically rather than being told it
                (see Scanner.scan()).

        Returns:
            A scanner.
        """
        raise NotImplementedError

    @abstractmethod
    def create_encoder(self, driven_segment: DrivenConveyorSegment) -> Encoder:
        """Build the encoder tracking the driven segment's belt travel.

        Args:
            driven_segment: The driven segment whose belt travel this
                encoder tracks.

        Returns:
            An encoder.
        """
        raise NotImplementedError

    @abstractmethod
    def create_sensor(self, sensor_id: str) -> Sensor:
        """Build one binary presence/position sensor.

        Args:
            sensor_id: Identifier of the sensor (e.g. "SENSOR-ENTRY").

        Returns:
            A sensor.
        """
        raise NotImplementedError
