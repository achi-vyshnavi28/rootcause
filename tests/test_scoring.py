import pandas as pd

from evals.scoring import hit_rank, results_match


def test_extra_columns_and_order_are_allowed():
    gold = pd.DataFrame({"s": ["SP", "RJ"], "n": [10, 5]})
    got = pd.DataFrame({"state": ["RJ", "SP"], "orders": [5.0, 10.0], "share": [0.33, 0.67]})
    assert results_match(gold, got)


def test_wrong_value_or_row_count_fails():
    gold = pd.DataFrame({"n": [10]})
    assert not results_match(gold, pd.DataFrame({"n": [11]}))
    assert not results_match(gold, pd.DataFrame({"n": [10, 10]}))


def test_float_tolerance_and_dates():
    gold = pd.DataFrame({"m": [pd.Timestamp("2017-11-01")], "v": [4.0864]})
    got = pd.DataFrame({"month": ["2017-11-01"], "avg": [4.0865]})
    assert results_match(gold, got)


def test_hit_rank_is_case_insensitive():
    cands = [{"dimension": "customer_city", "segment": "sao paulo"}, {"dimension": "customer_state", "segment": "SP"}]
    assert hit_rank(cands, ("customer_state", "sp")) == 2
    assert hit_rank(cands, ("payment_type", "boleto")) is None
