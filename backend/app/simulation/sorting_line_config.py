"""Physical configuration for a SortingLine (see README section 32).

Bundles the parameters that describe a sorting line's physical layout
(segment/gravity-segment geometry, gate positions, routing, scanner
behavior) into one value object, instead of a long parameter list on
SortingLine.__init__. Building a variant (e.g.
app.simulation.scenarios._build_multi_gate_line) is then a matter of
constructing one SortingLineConfig, or `dataclasses.replace()`-ing an
existing one, rather than re-declaring every default at the call site.
"""

import random
from dataclasses import dataclass

DEFAULT_GATE_POSITIONS: dict[int, float] = {1: 7.0, 2: 9.0, 3: 11.0}
"""Gate positions along the conveyor, in meters (see README section 32)."""

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


@dataclass
class SortingLineConfig:
    """Physical configuration of one SortingLine.

    Attributes:
        segment_length: Length of the driven conveyor segment, in meters.
        segment_speed: Initial belt speed, in m/s.
        segment_max_speed: Maximum belt speed, in m/s.
        segment_acceleration: Belt acceleration/braking rate, in m/s^2.
        gate_positions: Position of each gate, in meters, keyed by
            gate_id. None defaults to DEFAULT_GATE_POSITIONS.
        routing_table: Maps a barcode to the gate_id it routes to. None
            defaults to DEFAULT_ROUTING_TABLE.
        scanner_error_rate: Probability, in [0, 1], that a scan fails to
            find a code (see README section 7).
        scanner_position: Position of the scanner along the conveyor, in
            meters.
        gravity_length: Length of the downstream gravity buffer segment,
            in meters.
        gravity_incline_angle: Incline angle of the gravity segment, in
            degrees (positive = downhill).
        gravity_friction_coefficient: Rolling/sliding friction coefficient
            of the gravity segment.
        gravity_roller_diameter: Roller diameter of the gravity segment,
            in meters.
        gravity_min_package_weight: Minimum package mass, in kg, below
            which a package won't move on the gravity segment.
        rng: Random source for the scanner's simulated error rate. Inject
            a seeded random.Random for deterministic scenarios.
    """

    segment_length: float = 20.0
    segment_speed: float = 1.0
    segment_max_speed: float = 2.0
    segment_acceleration: float = 0.5
    gate_positions: dict[int, float] | None = None
    routing_table: dict[str, int] | None = None
    scanner_error_rate: float = 0.0
    scanner_position: float = DEFAULT_SCANNER_POSITION
    gravity_length: float = DEFAULT_GRAVITY_LENGTH
    gravity_incline_angle: float = DEFAULT_GRAVITY_INCLINE_ANGLE
    gravity_friction_coefficient: float = DEFAULT_GRAVITY_FRICTION_COEFFICIENT
    gravity_roller_diameter: float = DEFAULT_GRAVITY_ROLLER_DIAMETER
    gravity_min_package_weight: float = DEFAULT_GRAVITY_MIN_PACKAGE_WEIGHT
    rng: random.Random | None = None

    def __post_init__(self) -> None:
        """Replace None gate_positions/routing_table with owned copies of the defaults.

        Copying (rather than aliasing DEFAULT_GATE_POSITIONS/
        DEFAULT_ROUTING_TABLE directly) keeps every SortingLineConfig's
        maps independent, so nothing a caller does to one config's dict
        can leak into another's.
        """
        if self.gate_positions is None:
            self.gate_positions = dict(DEFAULT_GATE_POSITIONS)
        else:
            self.gate_positions = dict(self.gate_positions)

        if self.routing_table is None:
            self.routing_table = dict(DEFAULT_ROUTING_TABLE)
        else:
            self.routing_table = dict(self.routing_table)
