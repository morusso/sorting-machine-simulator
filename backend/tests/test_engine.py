import pytest

from app.simulation.engine import EngineState, SimulationEngine


def test_initial_state_is_stopped():
    engine = SimulationEngine()
    assert engine.state == EngineState.STOPPED
    assert engine.clock.now() == 0.0


def test_start_transitions_to_running():
    engine = SimulationEngine()
    engine.start()
    assert engine.state == EngineState.RUNNING
    assert engine.clock.is_paused is False


def test_start_twice_raises():
    engine = SimulationEngine()
    engine.start()
    with pytest.raises(RuntimeError):
        engine.start()


def test_pause_freezes_clock():
    engine = SimulationEngine()
    engine.start()
    engine.clock.advance(2.0)
    engine.pause()
    assert engine.state == EngineState.PAUSED
    engine.clock.advance(5.0)
    assert engine.clock.now() == pytest.approx(2.0)


def test_pause_without_running_raises():
    engine = SimulationEngine()
    with pytest.raises(RuntimeError):
        engine.pause()


def test_resume_continues_from_paused():
    engine = SimulationEngine()
    engine.start()
    engine.clock.advance(1.0)
    engine.pause()
    engine.resume()
    assert engine.state == EngineState.RUNNING
    engine.clock.advance(1.0)
    assert engine.clock.now() == pytest.approx(2.0)


def test_resume_without_pause_raises():
    engine = SimulationEngine()
    with pytest.raises(RuntimeError):
        engine.resume()


def test_stop_preserves_elapsed_time():
    engine = SimulationEngine()
    engine.start()
    engine.clock.advance(3.0)
    engine.stop()
    assert engine.state == EngineState.STOPPED
    assert engine.clock.now() == pytest.approx(3.0)


def test_stop_when_already_stopped_raises():
    engine = SimulationEngine()
    with pytest.raises(RuntimeError):
        engine.stop()


def test_reset_zeroes_clock_and_state():
    engine = SimulationEngine()
    engine.start()
    engine.clock.advance(4.0)
    engine.pause()
    engine.reset()
    assert engine.state == EngineState.STOPPED
    assert engine.clock.now() == 0.0
    assert engine.clock.is_paused is False


def test_engine_accepts_injected_clock():
    from app.simulation.clock import Clock

    clock = Clock(speed_multiplier=2.0)
    engine = SimulationEngine(clock=clock)
    assert engine.clock is clock
