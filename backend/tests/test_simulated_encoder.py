import pytest

from app.devices.encoder.simulated_encoder import SimulatedEncoder
from app.domain.conveyor import DrivenConveyorSegment


def make_encoder(speed=1.0, resolution=1000, wheel_circumference=0.5):
    conveyor = DrivenConveyorSegment(length=20.0, speed=speed, max_speed=2.0, acceleration=0.5)
    encoder = SimulatedEncoder(conveyor, resolution=resolution, wheel_circumference=wheel_circumference)
    return conveyor, encoder


@pytest.mark.asyncio
async def test_starts_at_zero_pulses():
    _, encoder = make_encoder()
    assert await encoder.get_pulse_count() == 0


@pytest.mark.asyncio
async def test_pulse_count_scales_with_belt_travel():
    conveyor, encoder = make_encoder(speed=1.0, resolution=1000, wheel_circumference=0.5)
    conveyor.advance(1.0)
    assert await encoder.get_pulse_count() == 2000


@pytest.mark.asyncio
async def test_pulse_count_not_clamped_by_segment_length():
    conveyor, encoder = make_encoder(speed=10.0, resolution=1000, wheel_circumference=0.5)
    conveyor.advance(10.0)
    assert await encoder.get_pulse_count() == 200000


@pytest.mark.asyncio
async def test_pulse_count_reflects_speed_changes():
    conveyor, encoder = make_encoder(speed=1.0, resolution=1000, wheel_circumference=0.5)
    conveyor.advance(1.0)
    conveyor.speed = 2.0
    conveyor.advance(1.0)
    assert await encoder.get_pulse_count() == 6000


def test_pulses_per_meter_derived_from_resolution_and_wheel_circumference():
    _, encoder = make_encoder(resolution=1000, wheel_circumference=0.5)
    assert encoder.pulses_per_meter == pytest.approx(2000.0)


@pytest.mark.asyncio
async def test_simulate_error_freezes_pulse_count():
    conveyor, encoder = make_encoder(speed=1.0, resolution=1000, wheel_circumference=0.5)
    conveyor.advance(1.0)
    encoder.simulate_error()
    conveyor.advance(1.0)

    assert encoder.faulted is True
    assert await encoder.get_pulse_count() == 2000
