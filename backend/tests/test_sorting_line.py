import pytest

from app.domain.gate import GateState
from app.domain.package import PackageStatus
from app.simulation.sorting_line import DEFAULT_SCANNER_POSITION, SortingLine
from app.simulation.sorting_line_config import SortingLineConfig


@pytest.mark.asyncio
async def test_create_package_starts_unscanned_and_in_transit():
    line = SortingLine()
    package = await line.create_package("5901234567890")
    assert package.status == PackageStatus.IN_TRANSIT
    assert package.barcode is None
    assert package.destination is None
    assert package.package_id in line._unscanned_barcodes


@pytest.mark.asyncio
async def test_create_package_defaults_to_a_1kg_weight():
    line = SortingLine()
    package = await line.create_package("5901234567890")
    assert package.weight == 1.0


@pytest.mark.asyncio
async def test_create_package_accepts_a_custom_weight():
    line = SortingLine()
    package = await line.create_package("5901234567890", weight=3.5)
    assert package.weight == 3.5


@pytest.mark.asyncio
async def test_tick_does_not_scan_before_reaching_scanner_position():
    line = SortingLine()
    package = await line.create_package("5901234567890")
    line.engine.start()

    await line.tick(DEFAULT_SCANNER_POSITION / line.segment.speed - 0.5)

    assert line.controller.packages[package.package_id].barcode is None
    assert line.controller.packages[package.package_id].status == PackageStatus.IN_TRANSIT


@pytest.mark.asyncio
async def test_tick_scans_package_on_reaching_scanner_position():
    line = SortingLine()
    package = await line.create_package("5901234567890")
    line.engine.start()

    await line.tick(DEFAULT_SCANNER_POSITION / line.segment.speed + 0.1)

    updated = line.controller.packages[package.package_id]
    assert updated.barcode == "5901234567890"
    assert updated.destination == 1
    assert updated.status == PackageStatus.ASSIGNED
    assert package.package_id not in line._unscanned_barcodes


@pytest.mark.asyncio
async def test_tick_rejects_package_with_unroutable_barcode():
    line = SortingLine()
    package = await line.create_package("0000000000000")
    line.engine.start()

    await line.tick(DEFAULT_SCANNER_POSITION / line.segment.speed + 0.1)

    updated = line.controller.packages[package.package_id]
    assert updated.barcode == "0000000000000"
    assert updated.destination is None
    assert updated.status == PackageStatus.REJECTED


@pytest.mark.asyncio
async def test_snapshot_reflects_scanned_package():
    line = SortingLine()
    await line.create_package("5901234567890")
    line.engine.start()
    await line.tick(DEFAULT_SCANNER_POSITION / line.segment.speed + 0.1)

    snapshot = await line.snapshot()
    assert snapshot["type"] == "simulation_state"
    assert snapshot["engine_state"] == "RUNNING"
    assert snapshot["conveyor"]["target_speed"] == 1.0
    assert snapshot["conveyor"]["length"] == 20.0
    assert snapshot["gates"][0]["position"] == 7.0
    assert len(snapshot["packages"]) == 1
    assert snapshot["packages"][0]["gate"] == 1
    assert len(snapshot["gates"]) == 3
    assert snapshot["statistics"]["total_packages"] == 1


@pytest.mark.asyncio
async def test_package_travels_from_creation_to_sorted_gate_closed():
    line = SortingLine()
    await line.create_package("5901234567890")
    line.engine.start()

    for _ in range(200):
        await line.tick(0.1)

    package = next(iter(line.controller.packages.values()))
    assert package.status == PackageStatus.SORTED
    assert await line.gates[1].get_state() == GateState.CLOSED
    # It kept rolling down the belt after being sorted and, having reached
    # the end of the driven segment, was handed off to the gravity buffer.
    assert package.package_id in await line.gravity_segment.get_package_ids()


@pytest.mark.asyncio
async def test_package_reaching_end_of_driven_segment_hands_off_to_gravity():
    line = SortingLine(SortingLineConfig(segment_length=5.0))
    package = await line.create_package("0000000000000")  # unroutable -> rides to the end
    line.engine.start()

    for _ in range(80):
        await line.tick(0.1)

    assert package.package_id not in await line.segment.get_package_ids()
    assert package.package_id in await line.gravity_segment.get_package_ids()


@pytest.mark.asyncio
async def test_handoff_carries_over_entry_velocity_from_the_belt():
    line = SortingLine(SortingLineConfig(segment_length=5.0))
    package = await line.create_package("0000000000000")
    line.engine.start()

    for _ in range(80):
        await line.tick(0.1)
        if package.package_id in await line.gravity_segment.get_package_ids():
            break

    velocity = await line.gravity_segment.get_package_velocity(package.package_id)
    assert velocity == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_light_package_stalls_on_the_gravity_segment():
    line = SortingLine(SortingLineConfig(segment_length=5.0, gravity_min_package_weight=0.5))
    package = await line.create_package("0000000000000", weight=0.1)
    line.engine.start()

    for _ in range(200):
        await line.tick(0.1)

    position = await line.gravity_segment.get_package_position(package.package_id)
    assert position == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_heavy_package_clears_the_gravity_segment():
    line = SortingLine(
        SortingLineConfig(
            segment_length=5.0,
            gravity_length=1.0,
            gravity_incline_angle=90.0,
            gravity_friction_coefficient=0.0,
        )
    )
    package = await line.create_package("0000000000000", weight=2.0)
    line.engine.start()

    for _ in range(100):
        await line.tick(0.1)

    position = await line.gravity_segment.get_package_position(package.package_id)
    assert position == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_snapshot_includes_gravity_segment_packages():
    line = SortingLine(SortingLineConfig(segment_length=5.0))
    package = await line.create_package("0000000000000")
    line.engine.start()

    for _ in range(80):
        await line.tick(0.1)
        if package.package_id in await line.gravity_segment.get_package_ids():
            break

    snapshot = await line.snapshot()
    assert snapshot["gravity_segment"]["length"] == line.gravity_segment.length
    ids = [p["id"] for p in snapshot["gravity_segment"]["packages"]]
    assert package.package_id in ids


def test_reset_clears_unscanned_packages():
    line = SortingLine()
    line._unscanned_barcodes["PKG-000001"] = "5901234567890"
    line.reset()
    assert line._unscanned_barcodes == {}


def test_reset_preserves_original_configuration():
    line = SortingLine(SortingLineConfig(segment_speed=1.5, scanner_error_rate=0.1))
    line.reset()
    assert line.segment.speed == 1.5
    assert line.scanner.error_rate == 0.1


@pytest.mark.asyncio
async def test_encoder_pulse_count_increases_as_belt_moves():
    line = SortingLine()
    line.engine.start()

    assert await line.encoder.get_pulse_count() == 0
    await line.tick(1.0)
    assert await line.encoder.get_pulse_count() > 0


@pytest.mark.asyncio
async def test_controller_position_tracks_physical_position_via_encoder():
    line = SortingLine()
    package = await line.create_package("5901234567890")
    line.engine.start()

    for _ in range(30):
        await line.tick(0.1)

    physical_position = await line.segment.get_package_position(package.package_id)
    reported_position = line.controller.packages[package.package_id].position
    # Encoder-derived, so quantized to one pulse (see SimulatedEncoder
    # defaults: 1000 pulses/rev over a 0.5 m wheel -> 0.5 mm/pulse).
    assert reported_position == pytest.approx(physical_position, abs=0.001)


@pytest.mark.asyncio
async def test_entry_sensor_triggers_for_a_package_at_the_start():
    line = SortingLine()
    await line.create_package("5901234567890")

    await line.tick(0.0)

    assert await line.entry_sensor.is_triggered() is True


@pytest.mark.asyncio
async def test_entry_sensor_clears_once_package_moves_away():
    line = SortingLine()
    await line.create_package("5901234567890")
    line.engine.start()

    for _ in range(5):
        await line.tick(0.1)

    assert await line.entry_sensor.is_triggered() is False


@pytest.mark.asyncio
async def test_end_of_belt_sensor_triggers_near_segment_end():
    line = SortingLine(SortingLineConfig(segment_length=1.0))
    await line.create_package("0000000000000")
    line.engine.start()

    triggered_at_some_point = False
    for _ in range(20):
        await line.tick(0.1)
        if await line.end_of_belt_sensor.is_triggered():
            triggered_at_some_point = True
            break

    assert triggered_at_some_point


@pytest.mark.asyncio
async def test_snapshot_includes_encoder_and_sensors():
    line = SortingLine()
    line.engine.start()
    await line.tick(1.0)

    snapshot = await line.snapshot()
    assert snapshot["encoder"]["pulse_count"] > 0
    sensor_ids = {sensor["id"] for sensor in snapshot["sensors"]}
    assert sensor_ids == {"SENSOR-ENTRY", "SENSOR-END-OF-BELT"}


@pytest.mark.asyncio
async def test_entry_reference_cleaned_up_after_handoff_to_gravity():
    line = SortingLine(SortingLineConfig(segment_length=1.0))
    package = await line.create_package("0000000000000")
    line.engine.start()

    for _ in range(20):
        await line.tick(0.1)
        if package.package_id in await line.gravity_segment.get_package_ids():
            break

    assert package.package_id not in line._entry_references
