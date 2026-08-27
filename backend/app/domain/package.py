from enum import Enum

from pydantic import BaseModel


class PackageStatus(str, Enum):
    """Lifecycle states a package can move through on the sorting line.

    The valid transitions are: CREATED -> IN_TRANSIT -> SCANNED -> ASSIGNED
    -> WAITING_FOR_GATE -> SORTED, with IN_TRANSIT also able to branch to
    REJECTED, LOST, or ERROR.
    """

    CREATED = "CREATED"
    IN_TRANSIT = "IN_TRANSIT"
    SCANNED = "SCANNED"
    ASSIGNED = "ASSIGNED"
    WAITING_FOR_GATE = "WAITING_FOR_GATE"
    SORTED = "SORTED"
    REJECTED = "REJECTED"
    LOST = "LOST"
    ERROR = "ERROR"


class Package(BaseModel):
    """A single physical package tracked by the simulator.

    Attributes:
        package_id: Unique identifier of the package (e.g. "PKG-000123").
        barcode: Decoded barcode value, if the package has been scanned.
        position: Current position along the transport axis, in meters.
        velocity: Current velocity along the transport axis, in m/s.
        destination: Identifier of the gate the package is routed to.
        width: Package width, in meters.
        length: Package length, in meters.
        height: Package height, in meters.
        weight: Package mass, in kg. Only relevant on gravity segments (see
            README section 4.1a) — driven segments move every package at
            the same belt speed regardless of weight.
        status: Current lifecycle state of the package.
    """

    package_id: str
    barcode: str | None = None
    position: float = 0.0
    velocity: float = 0.0
    destination: int | None = None
    width: float
    length: float
    height: float
    weight: float = 1.0
    status: PackageStatus = PackageStatus.CREATED
