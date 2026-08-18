from app.domain.conveyor import ConveyorSegment


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
    """

    def __init__(
        self,
        length: float,
        incline_angle: float,
        friction_coefficient: float,
        roller_diameter: float,
        min_package_weight: float,
    ):
        """Initialize a gravity conveyor segment.

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

    async def get_package_position(self, package_id: str) -> float:
        """Return the current position of a package on this segment.

        Since there is no drive encoder on a gravity segment, the position
        must be derived from the physical motion model and presence
        sensors rather than from encoder pulses.

        Args:
            package_id: Identifier of the package to locate.

        Returns:
            The package's position along the segment, in meters.
        """
        raise NotImplementedError
