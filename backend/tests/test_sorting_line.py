import pytest

from app.domain.gate import GateState
from app.domain.package import PackageStatus
from app.simulation.sorting_line import DEFAULT_SCANNER_POSITION, SortingLine


@pytest.mark.asyncio
async def test_create_package_starts_unscanned_and_in_transit():
    line = SortingLine()
    package = await line.create_package("5901234567890")
    assert package.status == PackageStatus.IN_TRANSIT
    assert package.barcode is None
    assert package.destination is None
    assert package.package_id in line._unscanned_barcodes


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


def test_reset_clears_unscanned_packages():
    line = SortingLine()
    line._unscanned_barcodes["PKG-000001"] = "5901234567890"
    line.reset()
    assert line._unscanned_barcodes == {}


def test_reset_preserves_original_configuration():
    line = SortingLine(segment_speed=1.5, scanner_error_rate=0.1)
    line.reset()
    assert line.segment.speed == 1.5
    assert line.scanner.error_rate == 0.1
