import pytest

from app.controllers.controller import Controller
from app.devices.gates.simulated_gate import SimulatedGate
from app.domain.conveyor import DrivenConveyorSegment
from app.domain.gate import GateState
from app.domain.package import Package, PackageStatus
from app.domain.scanner import ScanEvent, ScanResult
from app.simulation.clock import Clock
from app.simulation.engine import SimulationEngine


def make_package(package_id="PKG-1"):
    return Package(package_id=package_id, width=0.25, length=0.40, height=0.20)


def make_controller(clock=None, gate_lead_distance=0.3, gate_clear_distance=0.3):
    clock = clock if clock is not None else Clock()
    gate = SimulatedGate(clock, open_time_ms=300, close_time_ms=300)
    controller = Controller(
        gates={1: gate},
        gate_positions={1: 7.0},
        routing_table={"5901234567890": 1},
        gate_lead_distances={1: gate_lead_distance},
        gate_clear_distances={1: gate_clear_distance},
        clock=clock,
    )
    return controller, gate, clock


def test_register_package_tracks_it():
    controller, _, _ = make_controller()
    package = make_package()
    controller.register_package(package)
    assert controller.packages["PKG-1"] is package


def test_handle_scan_result_code_detected_assigns_gate():
    controller, _, _ = make_controller()
    controller.register_package(make_package())
    result = ScanResult(
        event=ScanEvent.CODE_DETECTED,
        scan_id="SCAN-000001",
        package_id="PKG-1",
        code="5901234567890",
        position=1.0,
        confidence=0.98,
    )
    package = controller.handle_scan_result(result)
    assert package.barcode == "5901234567890"
    assert package.destination == 1
    assert package.status == PackageStatus.ASSIGNED


def test_handle_scan_result_unknown_barcode_rejects_package():
    controller, _, _ = make_controller()
    controller.register_package(make_package())
    result = ScanResult(
        event=ScanEvent.CODE_DETECTED,
        scan_id="SCAN-000001",
        package_id="PKG-1",
        code="0000000000000",
        position=1.0,
        confidence=0.98,
    )
    package = controller.handle_scan_result(result)
    assert package.destination is None
    assert package.status == PackageStatus.REJECTED


def test_handle_scan_result_code_not_found_marks_error():
    controller, _, _ = make_controller()
    controller.register_package(make_package())
    result = ScanResult(
        event=ScanEvent.CODE_NOT_FOUND,
        scan_id="SCAN-000001",
        package_id="PKG-1",
    )
    package = controller.handle_scan_result(result)
    assert package.status == PackageStatus.ERROR


def test_handle_scan_result_unknown_package_raises():
    controller, _, _ = make_controller()
    result = ScanResult(
        event=ScanEvent.CODE_NOT_FOUND,
        scan_id="SCAN-000001",
        package_id="PKG-UNKNOWN",
    )
    with pytest.raises(KeyError):
        controller.handle_scan_result(result)


def test_calculate_arrival_time():
    time_s = Controller.calculate_arrival_time(current_position=4.35, target_position=7.20, speed=1.0)
    assert time_s == pytest.approx(2.85)


def test_calculate_arrival_time_behind_target_raises():
    with pytest.raises(ValueError):
        Controller.calculate_arrival_time(current_position=8.0, target_position=7.0, speed=1.0)


def test_calculate_arrival_time_non_positive_speed_raises():
    with pytest.raises(ValueError):
        Controller.calculate_arrival_time(current_position=0.0, target_position=1.0, speed=0.0)


@pytest.mark.asyncio
async def test_update_package_position_opens_gate_within_lead_distance():
    controller, gate, _ = make_controller(gate_lead_distance=0.3)
    package = make_package()
    package.status = PackageStatus.ASSIGNED
    package.destination = 1
    controller.register_package(package)

    updated = await controller.update_package_position("PKG-1", 6.6)
    assert await gate.get_state() == GateState.CLOSED
    assert updated.status == PackageStatus.ASSIGNED

    updated = await controller.update_package_position("PKG-1", 6.8)
    assert await gate.get_state() == GateState.OPENING
    assert updated.status == PackageStatus.WAITING_FOR_GATE


@pytest.mark.asyncio
async def test_update_package_position_marks_error_when_gate_fails_to_open():
    controller, gate, _ = make_controller(gate_lead_distance=0.3)
    await gate.open()
    gate.simulate_error()
    package = make_package()
    package.status = PackageStatus.ASSIGNED
    package.destination = 1
    controller.register_package(package)

    updated = await controller.update_package_position("PKG-1", 6.8)
    assert await gate.get_state() == GateState.ERROR
    assert updated.status == PackageStatus.ERROR


@pytest.mark.asyncio
async def test_update_package_position_marks_sorted_on_arrival():
    controller, gate, clock = make_controller(gate_lead_distance=0.3)
    package = make_package()
    package.status = PackageStatus.WAITING_FOR_GATE
    package.destination = 1
    controller.register_package(package)
    await gate.open()
    clock.advance(0.3)

    updated = await controller.update_package_position("PKG-1", 7.0)
    assert updated.status == PackageStatus.SORTED
    assert await gate.get_state() == GateState.OPEN


@pytest.mark.asyncio
async def test_update_package_position_closes_gate_after_clear_distance():
    controller, gate, clock = make_controller(gate_lead_distance=0.3, gate_clear_distance=0.3)
    package = make_package()
    package.status = PackageStatus.WAITING_FOR_GATE
    package.destination = 1
    controller.register_package(package)
    await gate.open()
    clock.advance(0.3)

    updated = await controller.update_package_position("PKG-1", 7.0)
    assert updated.status == PackageStatus.SORTED
    assert await gate.get_state() == GateState.OPEN

    await controller.update_package_position("PKG-1", 7.3)
    assert await gate.get_state() == GateState.CLOSING


@pytest.mark.asyncio
async def test_update_package_position_keeps_gate_open_before_clear_distance():
    controller, gate, clock = make_controller(gate_lead_distance=0.3, gate_clear_distance=0.3)
    package = make_package()
    package.status = PackageStatus.WAITING_FOR_GATE
    package.destination = 1
    controller.register_package(package)
    await gate.open()
    clock.advance(0.3)
    await controller.update_package_position("PKG-1", 7.0)

    await controller.update_package_position("PKG-1", 7.1)
    assert await gate.get_state() == GateState.OPEN


@pytest.mark.asyncio
async def test_update_package_position_ignores_unassigned_package():
    controller, gate, _ = make_controller()
    package = make_package()
    controller.register_package(package)

    updated = await controller.update_package_position("PKG-1", 6.9)
    assert updated.status == PackageStatus.CREATED
    assert await gate.get_state() == GateState.CLOSED


@pytest.mark.asyncio
async def test_sync_from_segments_updates_tracked_package():
    controller, gate, _ = make_controller(gate_lead_distance=0.3)
    package = make_package()
    package.status = PackageStatus.ASSIGNED
    package.destination = 1
    controller.register_package(package)

    segment = DrivenConveyorSegment(length=20.0, speed=1.0, max_speed=2.0, acceleration=0.5)
    segment.add_package("PKG-1", position=6.8)

    await controller.sync_from_segments([segment])
    assert controller.packages["PKG-1"].position == pytest.approx(6.8)
    assert await gate.get_state() == GateState.OPENING


@pytest.mark.asyncio
async def test_sync_from_segments_ignores_untracked_packages():
    controller, _, _ = make_controller()
    segment = DrivenConveyorSegment(length=20.0, speed=1.0, max_speed=2.0, acceleration=0.5)
    segment.add_package("PKG-UNKNOWN", position=1.0)

    await controller.sync_from_segments([segment])
    assert "PKG-UNKNOWN" not in controller.packages


@pytest.mark.asyncio
async def test_engine_and_controller_drive_package_to_sorted():
    clock = Clock()
    engine = SimulationEngine(clock=clock)
    segment = DrivenConveyorSegment(length=20.0, speed=1.0, max_speed=2.0, acceleration=0.5)
    engine.add_segment(segment)

    controller, gate, _ = make_controller(clock=clock, gate_lead_distance=0.3, gate_clear_distance=0.3)
    package = make_package()
    package.status = PackageStatus.ASSIGNED
    package.destination = 1
    controller.register_package(package)
    segment.add_package("PKG-1", position=6.5)

    engine.start()
    for _ in range(12):
        engine.tick(0.1)
        await controller.sync_from_segments(engine.segments)

    assert controller.packages["PKG-1"].status == PackageStatus.SORTED
    assert await gate.get_state() == GateState.CLOSED


def test_register_package_records_statistics():
    controller, _, _ = make_controller()
    controller.register_package(make_package())
    assert controller.statistics.total_packages == 1


def test_handle_scan_result_records_scan_error():
    controller, _, _ = make_controller()
    controller.register_package(make_package())
    controller.handle_scan_result(
        ScanResult(event=ScanEvent.CODE_NOT_FOUND, scan_id="SCAN-000001", package_id="PKG-1")
    )
    assert controller.statistics.scan_errors == 1


def test_handle_scan_result_records_unknown_code():
    controller, _, _ = make_controller()
    controller.register_package(make_package())
    controller.handle_scan_result(
        ScanResult(
            event=ScanEvent.CODE_DETECTED,
            scan_id="SCAN-000001",
            package_id="PKG-1",
            code="0000000000000",
        )
    )
    assert controller.statistics.unknown_codes == 1
    assert controller.statistics.rejected_packages == 1


@pytest.mark.asyncio
async def test_update_package_position_records_gate_open_and_sorted():
    controller, _, clock = make_controller(gate_lead_distance=0.3, gate_clear_distance=0.3)
    package = make_package()
    package.status = PackageStatus.ASSIGNED
    package.destination = 1
    controller.register_package(package)

    await controller.update_package_position("PKG-1", 6.8)
    assert controller.statistics.events[-1].event_type == "GATE_OPEN"

    clock.advance(0.3)
    await controller.update_package_position("PKG-1", 7.0)
    assert controller.statistics.sorted_packages == 1


@pytest.mark.asyncio
async def test_update_package_position_records_gate_error():
    controller, gate, _ = make_controller(gate_lead_distance=0.3)
    await gate.open()
    gate.simulate_error()
    package = make_package()
    package.status = PackageStatus.ASSIGNED
    package.destination = 1
    controller.register_package(package)

    await controller.update_package_position("PKG-1", 6.8)
    assert controller.statistics.gate_errors == 1
