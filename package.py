from enum import Enum

from pydantic import BaseModel


class PackageStatus(str, Enum):
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
    package_id: str
    barcode: str | None = None
    position: float = 0.0
    velocity: float = 0.0
    destination: int | None = None
    width: float
    length: float
    height: float
    status: PackageStatus = PackageStatus.CREATED
