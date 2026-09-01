import pytest

from app.domain.gate import GateState
from app.domain.package import PackageStatus
from app.simulation.sorting_line import DEFAULT_SCANNER_POSITION, SortingLine
from app.simulation.sorting_line_config import GravitySegmentConfig, SortingLineConfig


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
    await line.tick(line.scanner_detection_delay_s + 0.1)  # let the read delay elapse

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
    await line.tick(line.scanner_detection_delay_s + 0.1)  # let the read delay elapse

    updated = line.controller.packages[package.package_id]
    assert updated.barcode == "0000000000000"
    assert updated.destination is None
    assert updated.status == PackageStatus.REJECTED


@pytest.mark.asyncio
async def test_scan_result_is_not_applied_before_the_read_delay_elapses():
    line = SortingLine()
    package = await line.create_package("5901234567890")
    line.engine.start()

    await line.tick(DEFAULT_SCANNER_POSITION / line.segment.speed + 0.1)

    updated = line.controller.packages[package.package_id]
    assert updated.barcode is None
    assert updated.status == PackageStatus.IN_TRANSIT
    assert package.package_id in line._pending_scans
    assert package.package_id in line._unscanned_barcodes


@pytest.mark.asyncio
async def test_scan_result_applies_once_the_read_delay_elapses():
    line = SortingLine()
    package = await line.create_package("5901234567890")
    line.engine.start()

    await line.tick(DEFAULT_SCANNER_POSITION / line.segment.speed + 0.1)
    await line.tick(line.scanner_detection_delay_s + 0.1)

    updated = line.controller.packages[package.package_id]
    assert updated.barcode == "5901234567890"
    assert package.package_id not in line._pending_scans


@pytest.mark.asyncio
async def test_zero_read_delay_scans_within_the_same_tick():
    line = SortingLine(SortingLineConfig(scanner_detection_delay_ms=0.0))
    package = await line.create_package("5901234567890")
    line.engine.start()

    await line.tick(DEFAULT_SCANNER_POSITION / line.segment.speed + 0.1)

    updated = line.controller.packages[package.package_id]
    assert updated.barcode == "5901234567890"


@pytest.mark.asyncio
async def test_default_scanner_detection_delay_matches_the_readme():
    line = SortingLine()
    assert line.scanner_detection_delay_s == pytest.approx(0.05)


@pytest.mark.asyncio
async def test_package_reaching_the_end_before_its_scan_resolves_is_cleaned_up():
    line = SortingLine(
        SortingLineConfig(segment_length=3.0, scanner_position=1.0, scanner_detection_delay_ms=1_000_000.0)
    )
    package = await line.create_package("0000000000000")
    line.engine.start()

    for _ in range(50):
        await line.tick(0.1)

    assert package.package_id not in line._pending_scans
    assert package.package_id not in line._unscanned_barcodes
    assert line.controller.packages[package.package_id].status == PackageStatus.LOST


@pytest.mark.asyncio
async def test_snapshot_reflects_scanned_package():
    line = SortingLine()
    await line.create_package("5901234567890")
    line.engine.start()
    await line.tick(DEFAULT_SCANNER_POSITION / line.segment.speed + 0.1)
    await line.tick(line.scanner_detection_delay_s + 0.1)  # let the read delay elapse

    snapshot = await line.snapshot()
    assert snapshot["type"] == "simulation_state"
    assert snapshot["engine_state"] == "RUNNING"
    assert snapshot["speed_multiplier"] == 1.0
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
    line = SortingLine(
        SortingLineConfig(
            segment_length=5.0,
            gravity_segments=[GravitySegmentConfig(id=1, position_start=5.0, min_package_weight=0.5)],
        )
    )
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
            gravity_segments=[
                GravitySegmentConfig(id=1, position_start=5.0, length=1.0, incline_angle=90.0, friction_coefficient=0.0)
            ],
        )
    )
    package = await line.create_package("0000000000000", weight=2.0)
    line.engine.start()

    for _ in range(100):
        await line.tick(0.1)

    position = await line.gravity_segment.get_package_position(package.package_id)
    assert position == pytest.approx(1.0)


def test_default_gravity_segments_is_a_single_chain_entry():
    line = SortingLine()
    assert line._gravity_chain == [1]
    assert line.gravity_segment is line.gravity_segments[1]


def test_gravity_chain_orders_by_position_start_not_list_order():
    line = SortingLine(
        SortingLineConfig(
            gravity_segments=[
                GravitySegmentConfig(id=2, position_start=25.0),
                GravitySegmentConfig(id=1, position_start=20.0),
            ]
        )
    )
    assert line._gravity_chain == [1, 2]
    assert line.gravity_segment is line.gravity_segments[1]


@pytest.mark.asyncio
async def test_package_clearing_the_first_gravity_segment_moves_to_the_next():
    line = SortingLine(
        SortingLineConfig(
            segment_length=5.0,
            gravity_segments=[
                GravitySegmentConfig(id=1, position_start=5.0, length=1.0, incline_angle=90.0, friction_coefficient=0.0),
                GravitySegmentConfig(id=2, position_start=6.0, length=1.0, incline_angle=90.0, friction_coefficient=0.0),
            ],
        )
    )
    package = await line.create_package("0000000000000", weight=1.0)
    line.engine.start()

    for _ in range(100):
        await line.tick(0.1)
        if package.package_id in await line.gravity_segments[2].get_package_ids():
            break

    assert package.package_id in await line.gravity_segments[2].get_package_ids()
    assert package.package_id not in await line.gravity_segments[1].get_package_ids()


@pytest.mark.asyncio
async def test_gravity_chain_handoff_carries_over_velocity():
    line = SortingLine(
        SortingLineConfig(
            segment_length=5.0,
            gravity_segments=[
                GravitySegmentConfig(id=1, position_start=5.0, length=0.5, incline_angle=90.0, friction_coefficient=0.0),
                GravitySegmentConfig(id=2, position_start=5.5, length=1.0, incline_angle=0.0, friction_coefficient=0.0),
            ],
        )
    )
    package = await line.create_package("0000000000000", weight=1.0)
    line.engine.start()

    for _ in range(100):
        await line.tick(0.1)
        if package.package_id in await line.gravity_segments[2].get_package_ids():
            break

    velocity = await line.gravity_segments[2].get_package_velocity(package.package_id)
    assert velocity > 0.0


@pytest.mark.asyncio
async def test_emergency_stop_engages_every_gravity_segments_stopper():
    line = SortingLine(
        SortingLineConfig(
            gravity_segments=[
                GravitySegmentConfig(id=1, position_start=20.0),
                GravitySegmentConfig(id=2, position_start=25.0),
            ]
        )
    )

    await line.emergency_stop()

    assert all(segment.stopper_engaged for segment in line.gravity_segments.values())


@pytest.mark.asyncio
async def test_snapshot_lists_every_gravity_segment_in_chain_order():
    line = SortingLine(
        SortingLineConfig(
            gravity_segments=[
                GravitySegmentConfig(id=2, position_start=25.0),
                GravitySegmentConfig(id=1, position_start=20.0),
            ]
        )
    )

    snapshot = await line.snapshot()

    assert [segment["id"] for segment in snapshot["gravity_segments"]] == [1, 2]


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
    assert len(snapshot["gravity_segments"]) == 1
    assert snapshot["gravity_segments"][0]["id"] == 1
    assert snapshot["gravity_segments"][0]["length"] == line.gravity_segment.length
    ids = [p["id"] for p in snapshot["gravity_segments"][0]["packages"]]
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
async def test_engine_speed_multiplier_scales_tick_advancement():
    line = SortingLine()
    line.engine.start()
    line.engine.set_speed_multiplier(10.0)

    await line.tick(1.0)

    assert line.clock.now() == pytest.approx(10.0)
    assert (await line.snapshot())["speed_multiplier"] == 10.0


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


@pytest.mark.asyncio
async def test_emergency_stop_halts_the_driven_conveyor():
    line = SortingLine()
    line.engine.start()

    await line.emergency_stop()

    assert line.segment.speed == 0.0
    assert line.segment.target_speed == 0.0


@pytest.mark.asyncio
async def test_emergency_stop_engages_the_gravity_stopper():
    line = SortingLine()

    await line.emergency_stop()

    assert line.gravity_segment.stopper_engaged is True


@pytest.mark.asyncio
async def test_emergency_stop_forces_every_gate_to_safe_state():
    line = SortingLine()
    await line.gates[1].open()

    await line.emergency_stop()

    for gate in line.gates.values():
        assert await gate.get_state() == GateState.SAFE_STATE


@pytest.mark.asyncio
async def test_emergency_stop_puts_the_controller_in_safe_mode():
    line = SortingLine()

    await line.emergency_stop()

    assert line.controller.safe_mode is True


@pytest.mark.asyncio
async def test_emergency_stop_stops_the_engine():
    line = SortingLine()
    line.engine.start()

    await line.emergency_stop()

    assert line.engine.state == "STOPPED"


@pytest.mark.asyncio
async def test_emergency_stop_idles_the_scanner():
    line = SortingLine()
    package = await line.create_package("5901234567890", position=DEFAULT_SCANNER_POSITION)

    await line.emergency_stop()
    await line.tick(0.0)

    assert package.package_id in line._unscanned_barcodes
    assert line.controller.packages[package.package_id].status == PackageStatus.IN_TRANSIT


@pytest.mark.asyncio
async def test_emergency_stop_never_raises_from_any_engine_state():
    stopped_line = SortingLine()
    await stopped_line.emergency_stop()

    running_line = SortingLine()
    running_line.engine.start()
    await running_line.emergency_stop()

    paused_line = SortingLine()
    paused_line.engine.start()
    paused_line.engine.pause()
    await paused_line.emergency_stop()


@pytest.mark.asyncio
async def test_snapshot_reports_eta_for_an_assigned_package():
    line = SortingLine()
    await line.create_package("5901234567890")  # routes to gate 1 at position 7.0
    line.engine.start()
    await line.tick(DEFAULT_SCANNER_POSITION / line.segment.speed + 0.1)
    await line.tick(line.scanner_detection_delay_s + 0.1)  # let the read delay elapse

    snapshot = await line.snapshot()
    remaining = 7.0 - snapshot["packages"][0]["position"]
    assert snapshot["packages"][0]["eta"] == pytest.approx(remaining / line.segment.speed)


@pytest.mark.asyncio
async def test_snapshot_reports_no_eta_before_a_package_is_assigned():
    line = SortingLine()
    await line.create_package("5901234567890")

    snapshot = await line.snapshot()

    assert snapshot["packages"][0]["eta"] is None


@pytest.mark.asyncio
async def test_package_overshooting_its_gate_in_one_tick_is_marked_lost():
    line = SortingLine()
    package = await line.create_package("5901234567890")  # routes to gate 1 at position 7.0
    line.engine.start()
    line.segment.speed = 100.0  # bypasses accel ramping; one tick jumps clean past the scanner, gate, and segment end

    await line.tick(1.0)

    assert line.controller.packages[package.package_id].status == PackageStatus.LOST
    assert line.controller.statistics.lost_packages == 1
    assert package.package_id in await line.gravity_segment.get_package_ids()


@pytest.mark.asyncio
async def test_conveyor_fault_is_reported_once():
    line = SortingLine()
    line.engine.start()
    line.segment.simulate_fault()

    await line.tick(0.1)
    await line.tick(0.1)

    assert line.controller.statistics.conveyor_stops == 1


@pytest.mark.asyncio
async def test_sensor_fault_is_reported_once():
    line = SortingLine()
    line.engine.start()
    line.entry_sensor.simulate_error()

    await line.tick(0.1)
    await line.tick(0.1)

    assert line.controller.statistics.sensor_errors == 1
    assert line.controller.statistics.events[-1].detail == "SENSOR-ENTRY"


@pytest.mark.asyncio
async def test_encoder_fault_is_reported_once():
    line = SortingLine()
    line.engine.start()
    line.encoder.simulate_error()

    await line.tick(0.1)
    await line.tick(0.1)

    assert line.controller.statistics.encoder_errors == 1


@pytest.mark.asyncio
async def test_stalled_light_package_on_gravity_segment_is_reported():
    line = SortingLine(
        SortingLineConfig(gravity_segments=[GravitySegmentConfig(id=1, position_start=20.0, min_package_weight=0.5)])
    )
    line.engine.start()
    line.gravity_segment.add_package("PKG-1", weight=0.1, position=1.0)

    for _ in range(30):
        await line.tick(0.1)

    assert line.controller.statistics.gravity_segment_stalls == 1
    assert line.controller.statistics.events[-1].event_type == "GRAVITY_SEGMENT_STALL"


@pytest.mark.asyncio
async def test_package_blocked_by_a_stalled_package_ahead_is_reported_as_jam():
    line = SortingLine(
        SortingLineConfig(
            gravity_segments=[
                GravitySegmentConfig(
                    id=1, position_start=20.0, min_package_weight=0.5, incline_angle=45.0, friction_coefficient=0.0
                )
            ]
        )
    )
    line.engine.start()
    line.gravity_segment.add_package("PKG-FRONT", weight=0.1, position=1.0)  # too light to move; stays put
    line.gravity_segment.add_package("PKG-BACK", weight=2.0, position=0.5)  # catches up and gets blocked behind it

    for _ in range(60):
        await line.tick(0.1)

    assert line.controller.statistics.gravity_segment_stalls == 1
    assert line.controller.statistics.gravity_segment_jams == 1


@pytest.mark.asyncio
async def test_snapshot_reflects_emergency_stop():
    line = SortingLine()
    await line.emergency_stop()

    snapshot = await line.snapshot()
    assert snapshot["emergency_stopped"] is True


@pytest.mark.asyncio
async def test_reset_clears_emergency_stop():
    line = SortingLine()
    await line.emergency_stop()

    line.reset()

    assert line.emergency_stopped is False
    assert line.controller.safe_mode is False
    assert await line.gates[1].get_state() == GateState.CLOSED
