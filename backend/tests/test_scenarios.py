import random
import time

import pytest

from app.simulation import scenarios


@pytest.mark.asyncio
async def test_run_normal_operation_sorts_every_package():
    result = await scenarios.run_normal_operation(package_count=20, spacing_s=1.0)
    assert result.total_packages == 20
    assert result.sorted_packages == 20
    assert result.rejected_packages == 0
    assert result.error_packages == 0


@pytest.mark.asyncio
async def test_run_high_speed_sorts_every_package_despite_minimal_spacing():
    result = await scenarios.run_high_speed(package_count=20)
    assert result.total_packages == 20
    assert result.sorted_packages == 20


@pytest.mark.asyncio
async def test_run_scan_errors_produces_rejections_and_errors():
    result = await scenarios.run_scan_errors(
        package_count=50,
        unreadable_rate=0.2,
        incorrect_rate=0.1,
        rng=random.Random(42),
    )
    assert result.total_packages == 50
    assert result.sorted_packages + result.rejected_packages + result.error_packages == 50
    # 1 in 10 packages carries an unroutable barcode; some of those may
    # instead fail to read at all and surface as an error, not a rejection.
    assert result.rejected_packages <= 5
    assert result.error_packages > 0


@pytest.mark.asyncio
async def test_run_variable_speed_still_sorts_every_package():
    result = await scenarios.run_variable_speed(package_count=10)
    assert result.total_packages == 10
    assert result.sorted_packages == 10
    assert result.rejected_packages == 0
    assert result.error_packages == 0


@pytest.mark.asyncio
async def test_run_gate_failure_marks_only_packages_routed_to_it_as_error():
    result = await scenarios.run_gate_failure(package_count=6, failed_gate_id=3, spacing_s=1.0)
    assert result.total_packages == 6
    assert result.error_packages == 2
    assert result.sorted_packages == 4
    assert result.rejected_packages == 0


@pytest.mark.asyncio
async def test_run_jam_leaves_the_package_unsorted():
    result = await scenarios.run_jam(stall_after_s=1.0, max_time_s=10.0)
    assert result.total_packages == 1
    assert result.unsorted_packages == 1
    assert result.sorted_packages == 0
    assert result.rejected_packages == 0
    assert result.error_packages == 0


@pytest.mark.asyncio
async def test_run_load_test_scales_gates_and_routing_to_gate_count():
    result = await scenarios.run_load_test(package_count=100, gate_count=10, spacing_s=0.2, segment_length=30.0)
    assert result.total_packages == 100
    assert result.sorted_packages == 100
    assert result.rejected_packages == 0
    assert result.error_packages == 0


@pytest.mark.asyncio
@pytest.mark.slow
async def test_run_load_test_handles_10000_packages_without_critical_errors():
    """README section 37's success criterion: 10,000+ packages simulated
    without critical errors. Excluded from the default test run (see
    pytest.ini) since it takes several seconds; run explicitly with
    `pytest -m slow`.
    """
    start = time.perf_counter()
    result = await scenarios.run_load_test(package_count=10_000, gate_count=10, spacing_s=0.2, segment_length=30.0)
    wall_time_s = time.perf_counter() - start

    assert result.total_packages == 10_000
    assert result.unsorted_packages == 0
    assert result.sorted_packages == 10_000
    assert result.rejected_packages == 0
    assert result.error_packages == 0
    # Soft performance guard: catches a severe regression, not tuned as a
    # precise benchmark (~9s measured locally for this run).
    assert wall_time_s < 60.0


@pytest.mark.asyncio
async def test_run_gravity_segment_clears_on_steep_frictionless_incline():
    result = await scenarios.run_gravity_segment(
        weight=1.0, incline_angle=90.0, friction_coefficient=0.0, length=3.0, duration_s=2.0
    )
    assert result["cleared"] is True
    assert result["final_position"] == pytest.approx(3.0)


@pytest.mark.asyncio
async def test_run_gravity_segment_stalls_on_flat_high_friction_segment():
    result = await scenarios.run_gravity_segment(
        weight=1.0, incline_angle=0.0, friction_coefficient=1.0, length=3.0, duration_s=2.0
    )
    assert result["cleared"] is False
    assert result["final_position"] == pytest.approx(0.0)
