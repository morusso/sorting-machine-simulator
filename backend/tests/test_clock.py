import pytest

from app.simulation.clock import Clock


def test_starts_at_zero():
    clock = Clock()
    assert clock.now() == 0.0


def test_advance_accumulates_time():
    clock = Clock()
    clock.advance(1.0)
    clock.advance(0.5)
    assert clock.now() == pytest.approx(1.5)


def test_speed_multiplier_scales_advance():
    clock = Clock(speed_multiplier=10.0)
    clock.advance(1.0)
    assert clock.now() == pytest.approx(10.0)


def test_paused_clock_ignores_advance():
    clock = Clock()
    clock.advance(1.0)
    clock.pause()
    clock.advance(5.0)
    assert clock.now() == pytest.approx(1.0)
    assert clock.is_paused is True


def test_resume_continues_advancing():
    clock = Clock()
    clock.pause()
    clock.advance(5.0)
    clock.resume()
    clock.advance(2.0)
    assert clock.now() == pytest.approx(2.0)
    assert clock.is_paused is False


def test_reset_clears_time_and_pause_state():
    clock = Clock()
    clock.advance(3.0)
    clock.pause()
    clock.reset()
    assert clock.now() == 0.0
    assert clock.is_paused is False


def test_negative_dt_raises():
    clock = Clock()
    with pytest.raises(ValueError):
        clock.advance(-1.0)


def test_set_speed_multiplier_changes_subsequent_advance():
    clock = Clock()
    clock.advance(1.0)
    clock.set_speed_multiplier(10.0)
    clock.advance(1.0)
    assert clock.now() == pytest.approx(11.0)


def test_set_speed_multiplier_takes_effect_while_paused():
    clock = Clock()
    clock.pause()
    clock.set_speed_multiplier(100.0)
    clock.resume()
    clock.advance(1.0)
    assert clock.now() == pytest.approx(100.0)


@pytest.mark.parametrize("invalid_multiplier", [0.0, -1.0])
def test_set_speed_multiplier_rejects_non_positive(invalid_multiplier):
    clock = Clock()
    with pytest.raises(ValueError):
        clock.set_speed_multiplier(invalid_multiplier)
