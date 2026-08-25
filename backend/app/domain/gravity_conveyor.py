import math
from dataclasses import dataclass

from app.domain.conveyor import ConveyorSegment

GRAVITY = 9.81
"""Standard gravitational acceleration, in m/s^2, used by the segment's
motion model (see README section 4.1a)."""


@dataclass
class _TrackedPackage:
    """Per-package kinematic state tracked on a gravity segment.

    Attributes:
        position: Current position along the segment, in meters.
        velocity: Current velocity along the segment, in m/s.
        weight: Package mass, in kg.
    """

    position: float
    velocity: float
    weight: float


class GravityConveyorSegment(ConveyorSegment):
    """An unpowered roller/slide segment driven purely by incline and gravity.

    Unlike a driven segment, package speed here is not set by the
    controller: it results from a physical simulation based on incline
    angle, friction, and package mass, so different packages may move at
    different speeds on the same segment.

    Attributes:
        length: Length of the segment, in meters.
        incline_angle: Incline angle, in degrees (positive = downhill).
        friction_coefficient: Rolling/sliding friction coefficient.
        roller_diameter: Roller diameter, in meters (roller variant only).
        min_package_weight: Minimum package mass, in kg, below which a
            package may not move at all.
        stopper_engaged: Whether the segment's mechanical stopper/latch is
            currently blocking movement (see README section 26: a gravity
            segment has no motor to disable, so EMERGENCY_STOP must be
            modeled as this separate mechanism instead).
    """

    def __init__(
        self,
        length: float,
        incline_angle: float,
        friction_coefficient: float,
        roller_diameter: float,
        min_package_weight: float,
    ):
        """Initialize a gravity conveyor segment, with the stopper released.

        Args:
            length: Length of the segment, in meters.
            incline_angle: Incline angle, in degrees (positive = downhill).
            friction_coefficient: Rolling/sliding friction coefficient.
            roller_diameter: Roller diameter, in meters (roller variant
                only).
            min_package_weight: Minimum package mass, in kg, below which a
                package may not move at all.
        """
        self.length = length
        self.incline_angle = incline_angle
        self.friction_coefficient = friction_coefficient
        self.roller_diameter = roller_diameter
        self.min_package_weight = min_package_weight
        self.stopper_engaged = False
        self._packages: dict[str, _TrackedPackage] = {}

    def engage_stopper(self) -> None:
        """Engage the mechanical stopper, freezing all packages in place.

        Unlike a driven segment's emergency_stop(), there is no motor to
        disable here — the stopper is a separate physical mechanism that
        blocks packages outright, independent of the segment's incline/
        friction physics (see README section 26).
        """
        self.stopper_engaged = True
        for state in self._packages.values():
            state.velocity = 0.0

    def release_stopper(self) -> None:
        """Release the mechanical stopper, letting normal physics resume."""
        self.stopper_engaged = False

    @property
    def acceleration(self) -> float:
        """Net acceleration along the segment, in m/s^2.

        Computed as g*sin(incline_angle) - g*friction_coefficient*
        cos(incline_angle) (see README section 4.1a). Depends only on
        incline and friction, not on package weight. A negative value
        means packages decelerate rather than accelerate on this segment.

        Returns:
            The segment's net acceleration, in m/s^2.
        """
        theta = math.radians(self.incline_angle)
        return GRAVITY * math.sin(theta) - GRAVITY * self.friction_coefficient * math.cos(theta)

    def add_package(
        self,
        package_id: str,
        weight: float,
        position: float = 0.0,
        velocity: float = 0.0,
    ) -> None:
        """Start tracking a package on this segment.

        Args:
            package_id: Identifier of the package entering the segment.
            weight: Package mass, in kg. Below min_package_weight, the
                package will not move.
            position: Initial position along the segment, in meters.
            velocity: Initial velocity entering the segment, in m/s (see
                README section 4.1a: exit speed depends on entry speed).
        """
        self._packages[package_id] = _TrackedPackage(position=position, velocity=velocity, weight=weight)

    def remove_package(self, package_id: str) -> None:
        """Stop tracking a package on this segment (e.g. it exits onto the
        next segment or is handed off by the controller).

        Args:
            package_id: Identifier of the package leaving the segment.

        Raises:
            KeyError: If the package is not currently on this segment.
        """
        del self._packages[package_id]

    def advance(self, dt: float) -> None:
        """Advance every tracked package's position and velocity by dt.

        Applies the segment's constant acceleration to each package,
        except those below min_package_weight, which stay put entirely.
        Velocity never goes negative — a package that decelerates to a
        stop stays stopped rather than rolling back uphill. A package is
        also prevented from overtaking the package ahead of it on the
        segment, modeling pile-up/accumulation (see README section 4.1a).
        A no-op while the stopper is engaged (see engage_stopper()).

        Args:
            dt: Elapsed simulation time to advance by, in seconds.

        Raises:
            ValueError: If dt is negative.
        """
        if dt < 0:
            raise ValueError("dt must be non-negative")
        if self.stopper_engaged:
            return

        a = self.acceleration
        ahead_position: float | None = None
        for _, state in sorted(self._packages.items(), key=lambda item: -item[1].position):
            if state.weight < self.min_package_weight:
                state.velocity = 0.0
            else:
                new_position = state.position + state.velocity * dt + 0.5 * a * dt * dt
                state.velocity = max(0.0, state.velocity + a * dt)
                state.position = max(0.0, min(new_position, self.length))

            if ahead_position is not None and state.position > ahead_position:
                state.position = ahead_position
                state.velocity = 0.0

            ahead_position = state.position

    async def get_package_position(self, package_id: str) -> float:
        """Return the current position of a package on this segment.

        Args:
            package_id: Identifier of the package to locate.

        Returns:
            The package's position along the segment, in meters.

        Raises:
            KeyError: If the package is not currently on this segment.
        """
        return self._packages[package_id].position

    async def get_package_velocity(self, package_id: str) -> float:
        """Return the current velocity of a package on this segment.

        Unlike a driven segment's uniform belt speed, velocity varies per
        package here, so it is exposed alongside position (e.g. to detect
        a stalled package for a GRAVITY_SEGMENT_STALL error, see README
        section 25).

        Args:
            package_id: Identifier of the package to locate.

        Returns:
            The package's velocity along the segment, in m/s.

        Raises:
            KeyError: If the package is not currently on this segment.
        """
        return self._packages[package_id].velocity
