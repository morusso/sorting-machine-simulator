from abc import ABC, abstractmethod


class Scanner(ABC):
    """Interface for a barcode/QR/Data Matrix code reader.

    Implementations may be simulated or backed by a real device (e.g. over
    TCP), but expose the same interface so the controller does not need to
    know which one it is talking to.
    """

    @abstractmethod
    async def scan(self):
        """Read the next available code.

        Returns:
            An implementation-defined scan result (e.g. a decoded code or a
            "no code found" event).
        """
        raise NotImplementedError
