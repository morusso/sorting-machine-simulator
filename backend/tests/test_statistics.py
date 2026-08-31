import pytest

from app.simulation.statistics import Statistics


def test_record_package_created_increments_total():
    stats = Statistics()
    stats.record_package_created(0.0, "PKG-1")
    assert stats.total_packages == 1
    assert stats.events[-1].event_type == "PACKAGE_CREATED"


def test_record_scan_error_increments_counter():
    stats = Statistics()
    stats.record_scan_error(1.0, "PKG-1")
    assert stats.scan_errors == 1
    assert stats.events[-1].event_type == "CODE_NOT_FOUND"


def test_record_unknown_code_increments_rejected_and_unknown():
    stats = Statistics()
    stats.record_unknown_code(1.0, "PKG-1", "0000000000000")
    assert stats.unknown_codes == 1
    assert stats.rejected_packages == 1


def test_record_gate_error_increments_counter():
    stats = Statistics()
    stats.record_gate_error(1.0, "PKG-1", 3)
    assert stats.gate_errors == 1
    assert stats.events[-1].detail == "GATE-3"


def test_record_emergency_stop_logs_event():
    stats = Statistics()
    stats.record_emergency_stop(3.0)
    assert stats.events[-1].event_type == "EMERGENCY_STOP"
    assert stats.events[-1].timestamp == 3.0


def test_record_package_sorted_increments_counter():
    stats = Statistics()
    stats.record_package_sorted(2.0, "PKG-1", 1)
    assert stats.sorted_packages == 1


def test_average_scan_time_is_none_without_scans():
    stats = Statistics()
    assert stats.average_scan_time is None


def test_average_scan_time_averages_creation_to_scan_gap():
    stats = Statistics()
    stats.record_package_created(0.0, "PKG-1")
    stats.record_code_detected(2.0, "PKG-1", "5901234567890")
    stats.record_package_created(0.0, "PKG-2")
    stats.record_code_detected(4.0, "PKG-2", "5901234567890")
    assert stats.average_scan_time == pytest.approx(3.0)


def test_average_sort_time_is_none_without_sorts():
    stats = Statistics()
    assert stats.average_sort_time is None


def test_average_sort_time_averages_creation_to_sort_gap():
    stats = Statistics()
    stats.record_package_created(0.0, "PKG-1")
    stats.record_package_sorted(5.0, "PKG-1", 1)
    assert stats.average_sort_time == pytest.approx(5.0)


def test_summary_throughput_and_success_rate():
    stats = Statistics()
    for i in range(4):
        stats.record_package_created(0.0, f"PKG-{i}")
    stats.record_package_sorted(10.0, "PKG-0", 1)
    stats.record_package_sorted(10.0, "PKG-1", 1)
    stats.record_unknown_code(10.0, "PKG-2", "0000000000000")
    stats.record_scan_error(10.0, "PKG-3")

    summary = stats.summary(elapsed_time=10.0)
    assert summary["total_packages"] == 4
    assert summary["sorted_packages"] == 2
    assert summary["rejected_packages"] == 1
    assert summary["scan_errors"] == 1
    assert summary["error_packages"] == 1
    assert summary["throughput"] == pytest.approx(0.2)
    assert summary["packages_per_second"] == pytest.approx(0.4)
    assert summary["success_rate"] == pytest.approx(0.5)


def test_summary_handles_zero_elapsed_time_and_no_packages():
    stats = Statistics()
    summary = stats.summary(elapsed_time=0.0)
    assert summary["throughput"] == 0.0
    assert summary["packages_per_second"] == 0.0
    assert summary["success_rate"] is None
