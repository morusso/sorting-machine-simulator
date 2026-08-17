from app.domain.conveyor import ConveyorSegment


class GravityConveyorSegment(ConveyorSegment):
    def __init__(
        self,
        length: float,
        incline_angle: float,
        friction_coefficient: float,
        roller_diameter: float,
        min_package_weight: float,
    ):
        self.length = length
        self.incline_angle = incline_angle
        self.friction_coefficient = friction_coefficient
        self.roller_diameter = roller_diameter
        self.min_package_weight = min_package_weight

    async def get_package_position(self, package_id: str) -> float:
        raise NotImplementedError
