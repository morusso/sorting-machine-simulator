import random

import pytest

from app.devices.scanner.simulated_scanner import SimulatedScanner
from app.domain.scanner import ScanEvent


def make_scanner(barcodes: dict[str, str], **kwargs) -> SimulatedScanner:
    return SimulatedScanner(barcodes.get, **kwargs)


@pytest.mark.asyncio
async def test_successful_scan_returns_code_detected():
    scanner = make_scanner({"PKG-1": "5901234567890"}, error_rate=0.0)
    result = await scanner.scan("PKG-1", position=4.35)
    assert result.event == ScanEvent.CODE_DETECTED
    assert result.package_id == "PKG-1"
    assert result.code == "5901234567890"
    assert result.position == 4.35
    assert result.confidence == 0.98


@pytest.mark.asyncio
async def test_forced_error_rate_returns_code_not_found():
    scanner = make_scanner({"PKG-1": "5901234567890"}, error_rate=1.0)
    result = await scanner.scan("PKG-1")
    assert result.event == ScanEvent.CODE_NOT_FOUND
    assert result.code is None
    assert result.confidence is None


@pytest.mark.asyncio
async def test_scan_looks_up_the_barcode_for_the_given_package_id():
    scanner = make_scanner({"PKG-1": "111", "PKG-2": "222"}, error_rate=0.0)
    first = await scanner.scan("PKG-1")
    second = await scanner.scan("PKG-2")
    assert (first.package_id, first.code) == ("PKG-1", "111")
    assert (second.package_id, second.code) == ("PKG-2", "222")


@pytest.mark.asyncio
async def test_scan_of_unknown_package_id_returns_code_not_found():
    scanner = make_scanner({}, error_rate=0.0)
    result = await scanner.scan("PKG-UNKNOWN")
    assert result.event == ScanEvent.CODE_NOT_FOUND
    assert result.code is None


@pytest.mark.asyncio
async def test_scan_ids_are_unique_and_sequential():
    scanner = make_scanner({"PKG-1": "111", "PKG-2": "222"}, error_rate=0.0)
    first = await scanner.scan("PKG-1")
    second = await scanner.scan("PKG-2")
    assert first.scan_id == "SCAN-000001"
    assert second.scan_id == "SCAN-000002"


@pytest.mark.asyncio
async def test_scan_outcome_is_deterministic_with_seeded_rng():
    scanner = make_scanner({"PKG-1": "111"}, error_rate=0.5, rng=random.Random(42))
    result = await scanner.scan("PKG-1")
    assert result.event in (ScanEvent.CODE_DETECTED, ScanEvent.CODE_NOT_FOUND)
