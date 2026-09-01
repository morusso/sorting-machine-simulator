import pytest

from app.domain.conveyor import DrivenConveyorSegment


def make_segment(length=20.0, speed=1.0, max_speed=2.0, acceleration=0.5):
    return DrivenConveyorSegment(length=length, speed=speed, max_speed=max_speed, acceleration=acceleration)


@pytest.mark.asyncio
async def test_added_package_starts_at_given_position():
    segment = make_segment()
    segment.add_package("PKG-1", position=2.0)
    assert await segment.get_package_position("PKG-1") == 2.0


@pytest.mark.asyncio
async def test_added_package_defaults_to_zero():
    segment = make_segment()
    segment.add_package("PKG-1")
    assert await segment.get_package_position("PKG-1") == 0.0


@pytest.mark.asyncio
async def test_advance_moves_package_by_speed_times_dt():
    segment = make_segment(speed=1.0)
    segment.add_package("PKG-1", position=0.0)
    segment.advance(2.0)
    assert await segment.get_package_position("PKG-1") == pytest.approx(2.0)


@pytest.mark.asyncio
async def test_advance_moves_multiple_packages_independently():
    segment = make_segment(speed=1.0)
    segment.add_package("PKG-1", position=0.0)
    segment.add_package("PKG-2", position=5.0)
    segment.advance(1.0)
    assert await segment.get_package_position("PKG-1") == pytest.approx(1.0)
    assert await segment.get_package_position("PKG-2") == pytest.approx(6.0)


@pytest.mark.asyncio
async def test_position_clamped_at_segment_length():
    segment = make_segment(length=5.0, speed=10.0)
    segment.add_package("PKG-1", position=0.0)
    segment.advance(1.0)
    assert await segment.get_package_position("PKG-1") == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_speed_change_affects_subsequent_advance():
    segment = make_segment(speed=1.0)
    segment.add_package("PKG-1", position=0.0)
    segment.advance(1.0)
    segment.speed = 2.0
    segment.advance(1.0)
    assert await segment.get_package_position("PKG-1") == pytest.approx(3.0)


@pytest.mark.asyncio
async def test_get_position_of_unknown_package_raises():
    segment = make_segment()
    with pytest.raises(KeyError):
        await segment.get_package_position("MISSING")


def test_remove_package_stops_tracking():
    segment = make_segment()
    segment.add_package("PKG-1")
    segment.remove_package("PKG-1")
    with pytest.raises(KeyError):
        segment.remove_package("PKG-1")


def test_advance_with_negative_dt_raises():
    segment = make_segment()
    with pytest.raises(ValueError):
        segment.advance(-1.0)


@pytest.mark.asyncio
async def test_get_package_ids_returns_tracked_packages():
    segment = make_segment()
    segment.add_package("PKG-1")
    segment.add_package("PKG-2")
    assert set(await segment.get_package_ids()) == {"PKG-1", "PKG-2"}


@pytest.mark.asyncio
async def test_get_package_ids_empty_when_no_packages():
    segment = make_segment()
    assert await segment.get_package_ids() == []


def test_direct_speed_assignment_updates_target_speed():
    segment = make_segment(speed=1.0)
    segment.speed = 2.0
    assert segment.target_speed == 2.0


def test_set_speed_ramps_gradually_rather_than_jumping():
    segment = make_segment(speed=0.0, max_speed=2.0, acceleration=0.5)
    segment.set_speed(2.0)
    segment.advance(1.0)
    assert segment.speed == pytest.approx(0.5)
    segment.advance(1.0)
    assert segment.speed == pytest.approx(1.0)


def test_set_speed_does_not_overshoot_target():
    segment = make_segment(speed=1.0, max_speed=2.0, acceleration=0.5)
    segment.set_speed(2.0)
    segment.advance(10.0)
    assert segment.speed == pytest.approx(2.0)


def test_set_speed_brakes_gradually_rather_than_jumping():
    segment = make_segment(speed=2.0, max_speed=2.0, acceleration=0.5)
    segment.set_speed(0.0)
    segment.advance(1.0)
    assert segment.speed == pytest.approx(1.5)


def test_set_speed_braking_does_not_undershoot_target():
    segment = make_segment(speed=1.5, max_speed=2.0, acceleration=0.5)
    segment.set_speed(0.0)
    segment.advance(10.0)
    assert segment.speed == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_package_position_reflects_average_speed_during_ramp():
    segment = make_segment(speed=0.0, max_speed=2.0, acceleration=0.5)
    segment.add_package("PKG-1", position=0.0)
    segment.set_speed(2.0)
    segment.advance(1.0)
    # Speed ramps 0.0 -> 0.5 over this step; distance uses the average.
    assert await segment.get_package_position("PKG-1") == pytest.approx(0.25)


def test_set_speed_above_max_speed_raises():
    segment = make_segment(max_speed=2.0)
    with pytest.raises(ValueError):
        segment.set_speed(3.0)


def test_set_speed_negative_raises():
    segment = make_segment()
    with pytest.raises(ValueError):
        segment.set_speed(-1.0)


def test_emergency_stop_halts_immediately():
    segment = make_segment(speed=2.0, max_speed=2.0, acceleration=0.5)
    segment.emergency_stop()
    assert segment.speed == 0.0
    assert segment.target_speed == 0.0


@pytest.mark.asyncio
async def test_emergency_stop_prevents_further_movement():
    segment = make_segment(speed=1.0)
    segment.add_package("PKG-1", position=0.0)
    segment.emergency_stop()
    segment.advance(5.0)
    assert await segment.get_package_position("PKG-1") == pytest.approx(0.0)


def test_simulate_fault_stops_the_belt():
    segment = make_segment(speed=2.0)
    segment.simulate_fault()
    assert segment.faulted is True
    assert segment.speed == 0.0
    assert segment.target_speed == 0.0


def test_set_speed_after_fault_raises():
    segment = make_segment()
    segment.simulate_fault()
    with pytest.raises(RuntimeError):
        segment.set_speed(1.0)
