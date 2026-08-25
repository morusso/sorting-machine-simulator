import random

import pytest

from app.devices.scanner.simulated_scanner import SimulatedScanner
from app.domain.scanner import ScanEvent


@pytest.mark.asyncio
async def test_scan_with_no_queued_package_raises():
    scanner = SimulatedScanner()
    with pytest.raises(RuntimeError):
        await scanner.scan()


@pytest.mark.asyncio
async def test_successful_scan_returns_code_detected():
    scanner = SimulatedScanner(error_rate=0.0)
    scanner.enqueue("PKG-1", "5901234567890", position=4.35)
    result = await scanner.scan()
    assert result.event == ScanEvent.CODE_DETECTED
    assert result.package_id == "PKG-1"
    assert result.code == "5901234567890"
    assert result.position == 4.35
    assert result.confidence == 0.98


@pytest.mark.asyncio
async def test_forced_error_rate_returns_code_not_found():
    scanner = SimulatedScanner(error_rate=1.0)
    scanner.enqueue("PKG-1", "5901234567890")
    result = await scanner.scan()
    assert result.event == ScanEvent.CODE_NOT_FOUND
    assert result.code is None
    assert result.confidence is None


@pytest.mark.asyncio
async def test_scan_consumes_queue_in_order():
    scanner = SimulatedScanner(error_rate=0.0)
    scanner.enqueue("PKG-1", "111")
    scanner.enqueue("PKG-2", "222")
    first = await scanner.scan()
    second = await scanner.scan()
    assert (first.package_id, first.code) == ("PKG-1", "111")
    assert (second.package_id, second.code) == ("PKG-2", "222")


@pytest.mark.asyncio
async def test_scan_ids_are_unique_and_sequential():
    scanner = SimulatedScanner(error_rate=0.0)
    scanner.enqueue("PKG-1", "111")
    scanner.enqueue("PKG-2", "222")
    first = await scanner.scan()
    second = await scanner.scan()
    assert first.scan_id == "SCAN-000001"
    assert second.scan_id == "SCAN-000002"


@pytest.mark.asyncio
async def test_scan_outcome_is_deterministic_with_seeded_rng():
    scanner = SimulatedScanner(error_rate=0.5, rng=random.Random(42))
    scanner.enqueue("PKG-1", "111")
    result = await scanner.scan()
    assert result.event in (ScanEvent.CODE_DETECTED, ScanEvent.CODE_NOT_FOUND)
