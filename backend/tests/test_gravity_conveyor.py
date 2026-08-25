import math

import pytest

from app.domain.gravity_conveyor import GRAVITY, GravityConveyorSegment


def make_segment(
    length=20.0,
    incline_angle=90.0,
    friction_coefficient=0.0,
    roller_diameter=0.05,
    min_package_weight=0.2,
):
    return GravityConveyorSegment(
        length=length,
        incline_angle=incline_angle,
        friction_coefficient=friction_coefficient,
        roller_diameter=roller_diameter,
        min_package_weight=min_package_weight,
    )


def test_acceleration_matches_incline_and_friction_formula():
    segment = make_segment(incline_angle=8.0, friction_coefficient=0.04)
    theta = math.radians(8.0)
    expected = GRAVITY * math.sin(theta) - GRAVITY * 0.04 * math.cos(theta)
    assert segment.acceleration == pytest.approx(expected)


def test_flat_segment_with_no_friction_has_zero_acceleration():
    segment = make_segment(incline_angle=0.0, friction_coefficient=0.0)
    assert segment.acceleration == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_added_package_starts_at_given_position():
    segment = make_segment()
    segment.add_package("PKG-1", weight=1.0, position=2.0)
    assert await segment.get_package_position("PKG-1") == 2.0


@pytest.mark.asyncio
async def test_added_package_defaults_to_zero_position_and_velocity():
    segment = make_segment()
    segment.add_package("PKG-1", weight=1.0)
    assert await segment.get_package_position("PKG-1") == 0.0
    assert await segment.get_package_velocity("PKG-1") == 0.0


@pytest.mark.asyncio
async def test_advance_accelerates_package_downhill():
    # incline_angle=90, friction=0 -> acceleration == GRAVITY exactly.
    segment = make_segment(incline_angle=90.0, friction_coefficient=0.0)
    segment.add_package("PKG-1", weight=1.0, position=0.0, velocity=0.0)
    segment.advance(1.0)
    assert await segment.get_package_position("PKG-1") == pytest.approx(0.5 * GRAVITY)
    assert await segment.get_package_velocity("PKG-1") == pytest.approx(GRAVITY)


@pytest.mark.asyncio
async def test_exit_velocity_depends_on_entry_velocity():
    # Positions are kept far apart so pile-up clamping (tested separately)
    # cannot interfere with this comparison.
    segment = make_segment(incline_angle=90.0, friction_coefficient=0.0, length=1000.0)
    segment.add_package("SLOW", weight=1.0, position=0.0, velocity=0.0)
    segment.add_package("FAST", weight=1.0, position=100.0, velocity=5.0)
    segment.advance(1.0)
    slow_velocity = await segment.get_package_velocity("SLOW")
    fast_velocity = await segment.get_package_velocity("FAST")
    assert fast_velocity > slow_velocity
    assert fast_velocity == pytest.approx(slow_velocity + 5.0)


@pytest.mark.asyncio
async def test_package_decelerates_and_stops_rather_than_rolling_back():
    # incline_angle=0, friction=1.0 -> acceleration == -GRAVITY exactly.
    segment = make_segment(incline_angle=0.0, friction_coefficient=1.0, length=1000.0)
    segment.add_package("PKG-1", weight=1.0, position=0.0, velocity=0.0)
    segment.advance(1.0)
    assert await segment.get_package_position("PKG-1") == pytest.approx(0.0)
    assert await segment.get_package_velocity("PKG-1") == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_position_clamped_at_segment_length():
    segment = make_segment(length=5.0, incline_angle=90.0, friction_coefficient=0.0)
    segment.add_package("PKG-1", weight=1.0, position=0.0, velocity=100.0)
    segment.advance(1.0)
    assert await segment.get_package_position("PKG-1") == pytest.approx(5.0)


@pytest.mark.asyncio
async def test_package_below_min_weight_does_not_move():
    segment = make_segment(incline_angle=90.0, friction_coefficient=0.0, min_package_weight=0.5)
    segment.add_package("PKG-1", weight=0.1, position=1.0, velocity=0.0)
    segment.advance(5.0)
    assert await segment.get_package_position("PKG-1") == pytest.approx(1.0)
    assert await segment.get_package_velocity("PKG-1") == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_package_cannot_overtake_the_one_ahead():
    segment = make_segment(length=20.0, incline_angle=90.0, friction_coefficient=0.0)
    segment.add_package("FRONT", weight=1.0, position=5.0, velocity=0.0)
    segment.add_package("BACK", weight=1.0, position=0.0, velocity=10.0)
    segment.advance(1.0)
    front_position = await segment.get_package_position("FRONT")
    back_position = await segment.get_package_position("BACK")
    assert back_position == pytest.approx(front_position)
    assert await segment.get_package_velocity("BACK") == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_get_position_of_unknown_package_raises():
    segment = make_segment()
    with pytest.raises(KeyError):
        await segment.get_package_position("MISSING")


def test_remove_package_stops_tracking():
    segment = make_segment()
    segment.add_package("PKG-1", weight=1.0)
    segment.remove_package("PKG-1")
    with pytest.raises(KeyError):
        segment.remove_package("PKG-1")


def test_advance_with_negative_dt_raises():
    segment = make_segment()
    with pytest.raises(ValueError):
        segment.advance(-1.0)


def test_starts_with_stopper_released():
    segment = make_segment()
    assert segment.stopper_engaged is False


@pytest.mark.asyncio
async def test_engage_stopper_freezes_moving_package_immediately():
    segment = make_segment(incline_angle=90.0, friction_coefficient=0.0)
    segment.add_package("PKG-1", weight=1.0, position=0.0, velocity=3.0)
    segment.engage_stopper()
    assert await segment.get_package_velocity("PKG-1") == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_advance_is_a_no_op_while_stopper_engaged():
    segment = make_segment(incline_angle=90.0, friction_coefficient=0.0)
    segment.add_package("PKG-1", weight=1.0, position=1.0, velocity=0.0)
    segment.engage_stopper()
    segment.advance(5.0)
    assert await segment.get_package_position("PKG-1") == pytest.approx(1.0)
    assert await segment.get_package_velocity("PKG-1") == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_release_stopper_resumes_normal_physics():
    segment = make_segment(incline_angle=90.0, friction_coefficient=0.0)
    segment.add_package("PKG-1", weight=1.0, position=0.0, velocity=0.0)
    segment.engage_stopper()
    segment.advance(5.0)
    segment.release_stopper()
    segment.advance(1.0)
    assert await segment.get_package_position("PKG-1") == pytest.approx(0.5 * GRAVITY)
