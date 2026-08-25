from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel


class ScanEvent(str, Enum):
    CODE_DETECTED = "CODE_DETECTED"
    CODE_NOT_FOUND = "CODE_NOT_FOUND"


class ScanResult(BaseModel):
    event: ScanEvent
    scan_id: str
    package_id: str
    code: str | None = None
    position: float | None = None
    confidence: float | None = None


class Scanner(ABC):
    @abstractmethod
    async def scan(self) -> ScanResult:

        raise NotImplementedError
