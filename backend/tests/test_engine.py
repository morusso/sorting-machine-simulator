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


def test_tick_while_stopped_advances_nothing():
    engine = SimulationEngine()
    sim_dt = engine.tick(1.0)
    assert sim_dt == 0.0
    assert engine.clock.now() == 0.0


def test_tick_while_running_advances_clock_by_real_dt():
    engine = SimulationEngine()
    engine.start()
    sim_dt = engine.tick(1.0)
    assert sim_dt == pytest.approx(1.0)
    assert engine.clock.now() == pytest.approx(1.0)


def test_tick_scales_by_clock_speed_multiplier():
    from app.simulation.clock import Clock

    engine = SimulationEngine(clock=Clock(speed_multiplier=10.0))
    engine.start()
    sim_dt = engine.tick(1.0)
    assert sim_dt == pytest.approx(10.0)


def test_tick_while_paused_advances_nothing():
    engine = SimulationEngine()
    engine.start()
    engine.pause()
    sim_dt = engine.tick(5.0)
    assert sim_dt == 0.0
    assert engine.clock.now() == 0.0


@pytest.mark.asyncio
async def test_tick_advances_registered_segment():
    from app.domain.conveyor import DrivenConveyorSegment

    segment = DrivenConveyorSegment(length=20.0, speed=1.0, max_speed=2.0, acceleration=0.5)
    segment.add_package("PKG-1", position=0.0)
    engine = SimulationEngine()
    engine.add_segment(segment)
    engine.start()
    engine.tick(2.0)
    assert await segment.get_package_position("PKG-1") == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_tick_does_not_advance_segments_while_stopped():
    from app.domain.conveyor import DrivenConveyorSegment

    segment = DrivenConveyorSegment(length=20.0, speed=1.0, max_speed=2.0, acceleration=0.5)
    segment.add_package("PKG-1", position=0.0)
    engine = SimulationEngine()
    engine.add_segment(segment)
    engine.tick(5.0)
    assert await segment.get_package_position("PKG-1") == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_tick_advances_multiple_registered_segments():
    from app.domain.conveyor import DrivenConveyorSegment

    segment_a = DrivenConveyorSegment(length=20.0, speed=1.0, max_speed=2.0, acceleration=0.5)
    segment_b = DrivenConveyorSegment(length=20.0, speed=2.0, max_speed=2.0, acceleration=0.5)
    segment_a.add_package("PKG-A", position=0.0)
    segment_b.add_package("PKG-B", position=0.0)
    engine = SimulationEngine()
    engine.add_segment(segment_a)
    engine.add_segment(segment_b)
    engine.start()
    engine.tick(1.0)
    assert await segment_a.get_package_position("PKG-A") == pytest.approx(1.0)
    assert await segment_b.get_package_position("PKG-B") == pytest.approx(2.0)


def test_tick_with_negative_real_dt_raises():
    engine = SimulationEngine()
    engine.start()
    with pytest.raises(ValueError):
        engine.tick(-1.0)
