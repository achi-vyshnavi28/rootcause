from backend.agent.grounding import unsupported_numbers

EVIDENCE = {"delta": -512.0, "pct_change": -7.123, "share_of_change": 0.7134, "period": ["2018-04-01", "2018-05-01"]}


def test_rounded_and_percentage_numbers_are_supported():
    text = "Orders fell by 512 (-7.1%); MG explains 71% (71.34%) of the drop in April 2018 [Q2]."
    assert unsupported_numbers(text, EVIDENCE) == []


def test_invented_number_is_flagged():
    assert unsupported_numbers("Orders fell by 900.", EVIDENCE) == ["900"]


def test_query_ids_are_not_numbers():
    assert unsupported_numbers("See [Q12] and [Q3].", EVIDENCE) == []
