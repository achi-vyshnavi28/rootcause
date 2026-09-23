import pandas as pd
import pytest

from backend.tools.stats import mix_rate_decomposition, period_change, segment_contributions


def test_period_change():
    result = period_change(200, 150)
    assert result["delta"] == -50
    assert result["pct_change"] == pytest.approx(-25.0)


def test_period_change_from_zero_has_no_pct():
    assert period_change(0, 10)["pct_change"] is None


def test_segment_contributions_rank_and_shares():
    df = pd.DataFrame(
        {"state": ["SP", "RJ", "MG"], "orders_a": [100, 50, 50], "orders_b": [60, 50, 40]}
    )
    out = segment_contributions(df, "state", "orders_a", "orders_b")
    assert list(out["state"]) == ["SP", "MG", "RJ"]
    assert out["share_of_change"].sum() == pytest.approx(1.0)
    assert out.loc[0, "share_of_change"] == pytest.approx(0.8)  # SP explains 40 of the 50-order drop


def test_mix_rate_components_add_up_to_total_change():
    df = pd.DataFrame(
        {
            "region": ["north", "south"],
            "late_a": [10, 30],
            "orders_a": [100, 300],
            "late_b": [30, 30],
            "orders_b": [200, 200],
        }
    )
    r = mix_rate_decomposition(df, "region", "late_a", "orders_a", "late_b", "orders_b")
    assert r["rate_a"] == pytest.approx(40 / 400)
    assert r["rate_b"] == pytest.approx(60 / 400)
    assert r["mix_effect"] + r["rate_effect"] + r["interaction"] == pytest.approx(r["delta"])


def test_pure_mix_shift_has_zero_rate_effect():
    # Same late rate per region in both periods; only the order mix moves.
    df = pd.DataFrame(
        {
            "region": ["north", "south"],
            "late_a": [5, 30],
            "orders_a": [100, 100],
            "late_b": [9, 3],
            "orders_b": [180, 10],
        }
    )
    r = mix_rate_decomposition(df, "region", "late_a", "orders_a", "late_b", "orders_b")
    assert r["rate_effect"] == pytest.approx(0.0)
    assert r["interaction"] == pytest.approx(0.0)
    assert r["mix_effect"] == pytest.approx(r["delta"])
