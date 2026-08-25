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
