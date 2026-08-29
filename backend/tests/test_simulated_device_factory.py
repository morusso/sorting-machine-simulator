import pytest

from app.devices.encoder.simulated_encoder import SimulatedEncoder
from app.devices.gates.simulated_gate import SimulatedGate
from app.devices.scanner.simulated_scanner import SimulatedScanner
from app.devices.sensors.simulated_sensor import SimulatedSensor
from app.devices.simulated_device_factory import SimulatedDeviceFactory
from app.domain.conveyor import DrivenConveyorSegment
from app.domain.gravity_conveyor import GravityConveyorSegment
from app.simulation.clock import Clock

factory = SimulatedDeviceFactory()


def test_create_driven_segment_returns_configured_segment():
    segment = factory.create_driven_segment(length=20.0, speed=1.0, max_speed=2.0, acceleration=0.5)
    assert isinstance(segment, DrivenConveyorSegment)
    assert segment.length == 20.0
    assert segment.speed == 1.0


def test_create_gravity_segment_returns_configured_segment():
    segment = factory.create_gravity_segment(
        length=3.0, incline_angle=8.0, friction_coefficient=0.04, roller_diameter=0.05, min_package_weight=0.2
    )
    assert isinstance(segment, GravityConveyorSegment)
    assert segment.length == 3.0


@pytest.mark.asyncio
async def test_create_gate_returns_gate_bound_to_clock():
    clock = Clock()
    gate = factory.create_gate(clock, open_time_ms=300.0, close_time_ms=300.0)
    assert isinstance(gate, SimulatedGate)
    assert gate.open_time_ms == 300.0


def test_create_scanner_returns_configured_scanner():
    scanner = factory.create_scanner(error_rate=0.05, rng=None, barcode_lookup={"PKG-1": "111"}.get)
    assert isinstance(scanner, SimulatedScanner)
    assert scanner.error_rate == 0.05


@pytest.mark.asyncio
async def test_create_encoder_tracks_the_given_segment():
    segment = factory.create_driven_segment(length=20.0, speed=1.0, max_speed=2.0, acceleration=0.5)
    encoder = factory.create_encoder(segment)
    assert isinstance(encoder, SimulatedEncoder)
    segment.advance(1.0)
    assert await encoder.get_pulse_count() > 0


def test_create_sensor_returns_sensor_with_given_id():
    sensor = factory.create_sensor("SENSOR-ENTRY")
    assert isinstance(sensor, SimulatedSensor)
    assert sensor.sensor_id == "SENSOR-ENTRY"
