from aegis_shared.contracts import RecommendationAction as RA

from app.scoring import horizon_return, is_action_correct, is_contribution_correct


def test_horizon_return_basic():
    assert horizon_return(100.0, 130.0) == 0.3
    assert horizon_return(100.0, 90.0) == -0.1


def test_horizon_return_guards_none_and_zero():
    assert horizon_return(None, 100.0) is None
    assert horizon_return(100.0, None) is None
    assert horizon_return(0.0, 100.0) is None


def test_buy_correct_when_beats_benchmark():
    assert is_action_correct(RA.BUY, 0.30, 0.10, 0.05) is True
    assert is_action_correct(RA.STRONG_BUY, 0.05, 0.10, 0.05) is False


def test_sell_correct_when_underperforms_benchmark():
    assert is_action_correct(RA.SELL, -0.10, 0.05, 0.05) is True
    assert is_action_correct(RA.STRONG_SELL, 0.20, 0.05, 0.05) is False


def test_hold_correct_within_band():
    assert is_action_correct(RA.HOLD, 0.12, 0.10, 0.05) is True   # excess 0.02 within band
    assert is_action_correct(RA.HOLD, 0.30, 0.10, 0.05) is False  # excess 0.20 outside band


def test_contribution_correct_rewards_good_dissent():
    # supported a correct call -> correct
    assert is_contribution_correct(True, True) is True
    # supported a wrong call -> incorrect
    assert is_contribution_correct(True, False) is False
    # dissented from a wrong call -> correct (good dissent)
    assert is_contribution_correct(False, False) is True
    # dissented from a correct call -> incorrect
    assert is_contribution_correct(False, True) is False
