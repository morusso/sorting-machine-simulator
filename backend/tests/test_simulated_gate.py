import pytest

from app.devices.gates.simulated_gate import SimulatedGate
from app.domain.gate import GateState
from app.simulation.clock import Clock


def make_gate(open_time_ms=300, close_time_ms=300):
    clock = Clock()
    gate = SimulatedGate(clock, open_time_ms=open_time_ms, close_time_ms=close_time_ms)
    return clock, gate


@pytest.mark.asyncio
async def test_starts_closed():
    _, gate = make_gate()
    assert await gate.get_state() == GateState.CLOSED


@pytest.mark.asyncio
async def test_open_transitions_to_opening_immediately():
    _, gate = make_gate()
    await gate.open()
    assert await gate.get_state() == GateState.OPENING


@pytest.mark.asyncio
async def test_open_reaches_open_after_configured_duration():
    clock, gate = make_gate(open_time_ms=300)
    await gate.open()
    clock.advance(0.15)
    assert await gate.get_state() == GateState.OPENING
    clock.advance(0.15)
    assert await gate.get_state() == GateState.OPEN


@pytest.mark.asyncio
async def test_close_reaches_closed_after_configured_duration():
    clock, gate = make_gate(open_time_ms=300, close_time_ms=300)
    await gate.open()
    clock.advance(0.3)
    await gate.close()
    assert await gate.get_state() == GateState.CLOSING
    clock.advance(0.3)
    assert await gate.get_state() == GateState.CLOSED


@pytest.mark.asyncio
async def test_open_from_non_closed_state_raises():
    _, gate = make_gate()
    await gate.open()
    with pytest.raises(RuntimeError):
        await gate.open()


@pytest.mark.asyncio
async def test_close_from_non_open_state_raises():
    _, gate = make_gate()
    with pytest.raises(RuntimeError):
        await gate.close()


@pytest.mark.asyncio
async def test_simulate_error_during_opening():
    _, gate = make_gate()
    await gate.open()
    gate.simulate_error()
    assert await gate.get_state() == GateState.ERROR


def test_simulate_error_from_closed_raises():
    _, gate = make_gate()
    with pytest.raises(RuntimeError):
        gate.simulate_error()


@pytest.mark.asyncio
async def test_emergency_stop_from_closed_reaches_safe_state():
    _, gate = make_gate()
    await gate.emergency_stop()
    assert await gate.get_state() == GateState.SAFE_STATE


@pytest.mark.asyncio
async def test_emergency_stop_from_opening_reaches_safe_state():
    _, gate = make_gate()
    await gate.open()
    await gate.emergency_stop()
    assert await gate.get_state() == GateState.SAFE_STATE


@pytest.mark.asyncio
async def test_emergency_stop_from_open_reaches_safe_state():
    clock, gate = make_gate(open_time_ms=300)
    await gate.open()
    clock.advance(0.3)
    await gate.emergency_stop()
    assert await gate.get_state() == GateState.SAFE_STATE


@pytest.mark.asyncio
async def test_emergency_stop_from_error_reaches_safe_state():
    _, gate = make_gate()
    await gate.open()
    gate.simulate_error()
    await gate.emergency_stop()
    assert await gate.get_state() == GateState.SAFE_STATE


@pytest.mark.asyncio
async def test_open_from_safe_state_raises():
    _, gate = make_gate()
    await gate.emergency_stop()
    with pytest.raises(RuntimeError):
        await gate.open()


@pytest.mark.asyncio
async def test_close_from_safe_state_raises():
    _, gate = make_gate()
    await gate.emergency_stop()
    with pytest.raises(RuntimeError):
        await gate.close()
