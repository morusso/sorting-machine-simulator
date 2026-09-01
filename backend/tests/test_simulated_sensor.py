import pytest

from app.devices.sensors.simulated_sensor import SimulatedSensor


@pytest.mark.asyncio
async def test_starts_untriggered():
    sensor = SimulatedSensor("SENSOR-01")
    assert await sensor.is_triggered() is False


@pytest.mark.asyncio
async def test_trigger_sets_triggered():
    sensor = SimulatedSensor("SENSOR-01")
    sensor.trigger()
    assert await sensor.is_triggered() is True


@pytest.mark.asyncio
async def test_clear_resets_triggered():
    sensor = SimulatedSensor("SENSOR-01")
    sensor.trigger()
    sensor.clear()
    assert await sensor.is_triggered() is False


@pytest.mark.asyncio
async def test_simulate_error_freezes_current_reading():
    sensor = SimulatedSensor("SENSOR-01")
    sensor.trigger()
    sensor.simulate_error()
    sensor.clear()
    assert sensor.faulted is True
    assert await sensor.is_triggered() is True


@pytest.mark.asyncio
async def test_simulate_error_ignores_trigger_too():
    sensor = SimulatedSensor("SENSOR-01")
    sensor.simulate_error()
    sensor.trigger()
    assert await sensor.is_triggered() is False
