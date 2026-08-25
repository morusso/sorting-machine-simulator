from enum import Enum

from app.simulation.clock import Clock


class EngineState(str, Enum):
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"


class SimulationEngine:

    def __init__(self, clock: Clock | None = None):

        self.clock = clock if clock is not None else Clock()
        self.state = EngineState.STOPPED

    def start(self):

        if self.state != EngineState.STOPPED:
            raise RuntimeError(f"cannot start engine from state {self.state}")
        self.clock.resume()
        self.state = EngineState.RUNNING

    def pause(self):

        if self.state != EngineState.RUNNING:
            raise RuntimeError(f"cannot pause engine from state {self.state}")
        self.clock.pause()
        self.state = EngineState.PAUSED

    def resume(self):

        if self.state != EngineState.PAUSED:
            raise RuntimeError(f"cannot resume engine from state {self.state}")
        self.clock.resume()
        self.state = EngineState.RUNNING

    def stop(self):

        if self.state == EngineState.STOPPED:
            raise RuntimeError(f"cannot stop engine from state {self.state}")
        self.clock.pause()
        self.state = EngineState.STOPPED

    def reset(self):

        self.clock.reset()
        self.state = EngineState.STOPPED
