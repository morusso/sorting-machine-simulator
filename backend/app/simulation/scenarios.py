"""Predefined test scenarios (see README section 22)."""

import itertools
import random
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from app.domain.gravity_conveyor import GravityConveyorSegment
from app.domain.package import PackageStatus
from app.simulation.sorting_line import SortingLine

TICK_S = 0.1
"""Simulated-time step used to advance scenarios (see README section 21)."""

MAX_SIMULATED_TIME_S = 300.0
"""Safety cutoff so a scenario that never settles (e.g. a jam) still
returns instead of looping forever."""

UNROUTABLE_BARCODE = "0000000000000"
"""A barcode with no routing_table entry, used to simulate an incorrectly
read code (see README section 25, UNKNOWN_BARCODE)."""


@dataclass
class ScenarioResult:
    """Outcome of running a routing scenario to completion (or to the
    MAX_SIMULATED_TIME_S cutoff).

    Attributes:
        total_packages: Number of packages spawned during the run.
        sorted_packages: Number that reached SORTED.
        rejected_packages: Number that reached REJECTED (unroutable barcode).
        error_packages: Number that reached ERROR (failed scan or gate).
        elapsed_time: Simulated time the scenario ran for, in seconds.
    """

    total_packages: int
    sorted_packages: int
    rejected_packages: int
    error_packages: int
    elapsed_time: float

    @property
    def unsorted_packages(self) -> int:
        """Packages still in flight (neither sorted, rejected, nor errored)."""
        return self.total_packages - self.sorted_packages - self.rejected_packages - self.error_packages


def _round_robin_barcodes(routing_table: dict[str, int]) -> Iterable[str]:
    """Cycle through every routable barcode in routing_table, in order."""
    return itertools.cycle(routing_table.keys())


def _is_settled(line: SortingLine) -> bool:
    """Whether every tracked package has reached a terminal status."""
    terminal = (PackageStatus.SORTED, PackageStatus.REJECTED, PackageStatus.ERROR)
    return all(package.status in terminal for package in line.controller.packages.values())


def _summarize(line: SortingLine, elapsed_time: float) -> ScenarioResult:
    """Build a ScenarioResult from a sorting line's current package statuses."""
    statuses = [package.status for package in line.controller.packages.values()]
    return ScenarioResult(
        total_packages=len(statuses),
        sorted_packages=statuses.count(PackageStatus.SORTED),
        rejected_packages=statuses.count(PackageStatus.REJECTED),
        error_packages=statuses.count(PackageStatus.ERROR),
        elapsed_time=elapsed_time,
    )


async def _run_until_settled(
    line: SortingLine,
    spawn_schedule: list[tuple[float, str]],
    on_tick: Callable[[SortingLine, float], None] | None = None,
    max_time_s: float = MAX_SIMULATED_TIME_S,
    tick_s: float = TICK_S,
) -> ScenarioResult:
    """Spawn packages on schedule and tick until every package settles.

    Args:
        line: The sorting line to run.
        spawn_schedule: (spawn_time_s, barcode) pairs; a package is
            created once elapsed simulated time reaches spawn_time_s.
        on_tick: Optional hook called with (line, elapsed_time_s) before
            each tick, e.g. to change conveyor speed mid-run.
        max_time_s: Safety cutoff in case some package never settles.
        tick_s: Simulated-time step per iteration.

    Returns:
        A summary of every package's final status.
    """
    line.engine.start()
    elapsed = 0.0
    pending = sorted(spawn_schedule, key=lambda item: item[0])
    index = 0
    while elapsed < max_time_s:
        while index < len(pending) and pending[index][0] <= elapsed:
            await line.create_package(pending[index][1])
            index += 1
        if on_tick is not None:
            on_tick(line, elapsed)
        await line.tick(tick_s)
        elapsed += tick_s
        if index >= len(pending) and _is_settled(line):
            break
    return _summarize(line, elapsed)


async def run_normal_operation(package_count: int = 1000, spacing_s: float = 1.0) -> ScenarioResult:
    """Normal operation: package_count packages at 1.0 m/s, all correctly coded."""
    line = SortingLine(segment_speed=1.0)
    barcodes = _round_robin_barcodes(line.controller.routing_table)
    schedule = [(i * spacing_s, next(barcodes)) for i in range(package_count)]
    return await _run_until_settled(line, schedule)


async def run_high_speed(package_count: int = 1000, spacing_s: float = 0.5) -> ScenarioResult:
    """High speed: package_count packages at 2.0 m/s with minimal spacing.

    spacing_s=0.5 is the tightest spacing that still leaves each gate time
    to fully cycle (open, close) before the next package cycling through
    the same gate (every 3rd, given 3 gates) arrives — tighter spacing
    causes genuine gate contention (see Controller.update_package_position),
    which is a real system limit rather than something this scenario means
    to exercise.
    """
    line = SortingLine(segment_speed=2.0)
    barcodes = _round_robin_barcodes(line.controller.routing_table)
    schedule = [(i * spacing_s, next(barcodes)) for i in range(package_count)]
    return await _run_until_settled(line, schedule)


async def run_scan_errors(
    package_count: int = 1000,
    unreadable_rate: float = 0.05,
    incorrect_rate: float = 0.02,
    spacing_s: float = 1.0,
    rng: random.Random | None = None,
) -> ScenarioResult:
    """Scan errors: some codes fail to read, others read as an unroutable barcode.

    unreadable_rate drives the scanner's own simulated CODE_NOT_FOUND rate
    (-> package ERROR). incorrect_rate is applied deterministically instead
    (every 1/incorrect_rate-th package gets an unroutable barcode instead
    of a real one), so a correctly-read-but-unroutable code (-> REJECTED)
    is guaranteed to appear regardless of scanner randomness.
    """
    line = SortingLine(scanner_error_rate=unreadable_rate, rng=rng)
    good_barcodes = _round_robin_barcodes(line.controller.routing_table)
    incorrect_every = round(1 / incorrect_rate) if incorrect_rate > 0 else 0
    schedule = []
    for i in range(package_count):
        is_incorrect = incorrect_every and i % incorrect_every == 0
        barcode = UNROUTABLE_BARCODE if is_incorrect else next(good_barcodes)
        schedule.append((i * spacing_s, barcode))
    return await _run_until_settled(line, schedule)


async def run_variable_speed(package_count: int = 20, spacing_s: float = 1.5) -> ScenarioResult:
    """Variable speed: belt ramps through 0.5 -> 1.0 -> 1.5 -> 0.8 m/s while packages are in flight.

    See run_high_speed()'s docstring re: spacing_s needing enough margin
    for each gate to fully cycle between same-gate packages; variable
    speed needs extra margin on top of that since a speed change can
    compress the gap between two packages that were already close to a
    gate when it happened.
    """
    line = SortingLine(segment_speed=0.5)
    barcodes = _round_robin_barcodes(line.controller.routing_table)
    schedule = [(i * spacing_s, next(barcodes)) for i in range(package_count)]

    speed_changes = [(5.0, 1.0), (10.0, 1.5), (15.0, 0.8)]

    def apply_speed_changes(line: SortingLine, elapsed: float) -> None:
        while speed_changes and speed_changes[0][0] <= elapsed:
            _, speed = speed_changes.pop(0)
            line.segment.set_speed(speed)

    return await _run_until_settled(line, schedule, on_tick=apply_speed_changes)


async def run_gate_failure(package_count: int = 20, failed_gate_id: int = 3, spacing_s: float = 1.0) -> ScenarioResult:
    """Gate failure: failed_gate_id is stuck in ERROR before any package arrives.

    Packages routed to it end up ERROR (see Controller.update_package_position);
    packages routed elsewhere are unaffected.
    """
    line = SortingLine()
    await line.gates[failed_gate_id].open()
    line.gates[failed_gate_id].simulate_error()

    barcodes = _round_robin_barcodes(line.controller.routing_table)
    schedule = [(i * spacing_s, next(barcodes)) for i in range(package_count)]
    return await _run_until_settled(line, schedule)


async def run_jam(stall_after_s: float = 1.0, max_time_s: float = 10.0) -> ScenarioResult:
    """Jam: the belt stops mid-transit, so the package never leaves the sorting zone.

    Modeled as an emergency stop shortly after the package enters the
    conveyor — it never reaches the scanner, let alone a gate (see README
    section 26).
    """
    line = SortingLine()
    barcode = next(iter(line.controller.routing_table))
    await line.create_package(barcode)

    def stall_once(line: SortingLine, elapsed: float) -> None:
        if elapsed >= stall_after_s and line.segment.speed != 0.0:
            line.segment.emergency_stop()

    return await _run_until_settled(line, [], on_tick=stall_once, max_time_s=max_time_s)


def _build_multi_gate_line(gate_count: int, segment_length: float) -> SortingLine:
    """Build a SortingLine with gate_count evenly-spaced gates and a
    matching 1:1 routing table, for scenarios that need more routing
    capacity than the API's 3-gate default (see README section 33: up to
    50 gates should be supported).
    """
    usable_length = segment_length - 5.0
    gate_positions = {gate_id: 3.0 + gate_id * (usable_length / gate_count) for gate_id in range(1, gate_count + 1)}
    routing_table = {f"{9_000_000_000_000 + gate_id}": gate_id for gate_id in range(1, gate_count + 1)}
    return SortingLine(segment_length=segment_length, gate_positions=gate_positions, routing_table=routing_table)


async def run_load_test(
    package_count: int = 10_000,
    gate_count: int = 10,
    spacing_s: float = 0.2,
    segment_length: float = 30.0,
    tick_s: float = 0.2,
) -> ScenarioResult:
    """Load test: package_count packages through gate_count gates.

    Verifies README section 37's success criterion — 10,000+ packages
    simulated without critical errors — at a throughput within section
    33's stated 1-10 pkg/s range (spacing_s=0.2 -> 5 pkg/s). Spread across
    gate_count gates (rather than the API's usual 3) so that volume alone
    doesn't trigger the gate-contention edge case documented in
    run_high_speed() — that's a distinct, already-covered scenario, not
    what this one means to exercise.

    tick_s is coarser than the other scenarios' default (see TICK_S):
    correct here because gate triggering only depends on position
    crossing a threshold, not on tick granularity, and a coarser step
    keeps this scenario's own run time reasonable at 10,000+ packages.
    """
    line = _build_multi_gate_line(gate_count, segment_length)
    barcodes = _round_robin_barcodes(line.controller.routing_table)
    schedule = [(i * spacing_s, next(barcodes)) for i in range(package_count)]
    max_time_s = package_count * spacing_s + 60.0
    return await _run_until_settled(line, schedule, max_time_s=max_time_s, tick_s=tick_s)


async def run_gravity_segment(
    weight: float = 1.0,
    length: float = 3.0,
    incline_angle: float = 8.0,
    friction_coefficient: float = 0.04,
    roller_diameter: float = 0.05,
    min_package_weight: float = 0.2,
    duration_s: float = 10.0,
    tick_s: float = TICK_S,
) -> dict:
    """Gravity segment: check whether a package of the given weight clears
    the segment, or stalls partway (see README section 4.1a).

    Returns:
        A dict with "cleared" (bool: reached the end of the segment within
        duration_s) and "final_position" (float, meters).
    """
    segment = GravityConveyorSegment(
        length=length,
        incline_angle=incline_angle,
        friction_coefficient=friction_coefficient,
        roller_diameter=roller_diameter,
        min_package_weight=min_package_weight,
    )
    segment.add_package("PKG-1", weight=weight)
    elapsed = 0.0
    while elapsed < duration_s:
        segment.advance(tick_s)
        elapsed += tick_s
    position = await segment.get_package_position("PKG-1")
    return {"cleared": position >= length, "final_position": position}
