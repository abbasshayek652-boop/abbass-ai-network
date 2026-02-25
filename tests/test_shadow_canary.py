from agents.modes.shadow import ModeState


def test_shadow_mode_all_shadow():
    state = ModeState(mode="shadow", canary_fraction=0.1)
    live, shadow = state.split(1.0)
    assert live == 0.0
    assert shadow == 1.0


def test_canary_mode_fraction():
    state = ModeState(mode="canary", canary_fraction=0.2)
    live, shadow = state.split(2.0)
    assert live == 0.4
    assert shadow == 1.6


def test_canary_errors_trigger_halt():
    state = ModeState(mode="canary", canary_fraction=0.5)
    for _ in range(state.stats.max_errors):
        state.record_error()
    assert state.should_halt() is True

