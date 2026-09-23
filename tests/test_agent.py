"""End-to-end agent tests: real graph, real SQL (DuckDB), scripted LLM replies."""

from backend.agent.graph import AgentDeps
from backend.agent.runner import run_question
from backend.llm import ScriptedLLM
from tests import fake_olist

APRIL_VS_MARCH = {
    "date_column": "order_purchase_timestamp",
    "period_a_start": "2018-03-01", "period_a_end": "2018-04-01",
    "period_b_start": "2018-04-01", "period_b_end": "2018-05-01",
}
NARRATIVE = {"summary": "Orders fell.", "root_cause_explanation": "See evidence.",
             "next_checks": ["Check the top segment."], "suggested_experiment": "Monitor it."}


def _deps(con, replies) -> AgentDeps:
    return AgentDeps(llm=ScriptedLLM(replies), run_sql=fake_olist.runner_for(con), schema_context=fake_olist.context)


def test_order_drop_is_traced_to_the_planted_state():
    con = fake_olist.build(drop_state="MG")
    replies = {
        "Route": [{"intent": "why_change", "reason": "asks why orders dropped"}],
        "MetricSpec": [{"metric_name": "orders", "kind": "total", "order_value_sql": "1", **APRIL_VS_MARCH}],
        "Narrative": [NARRATIVE],
    }
    result = run_question("Why did orders drop in April 2018?", "olist", _deps(con, replies), save=False)

    assert result["status"] == "ok"
    top = result["report"]["evidence"]["top_candidates"][0]
    assert (top["dimension"], top["segment"]) == ("customer_state", "MG")
    assert result["report"]["evidence"]["overall_change"]["delta"] < 0
    assert all(q.get("error") is None for q in result["queries"])
    assert result["report"]["confidence"] in {"high", "medium"}


def test_duplicate_payment_rows_are_reported_as_data_quality_issue():
    con = fake_olist.build(drop_state=None, duplicate_payments=True)
    replies = {
        "Route": [{"intent": "why_change", "reason": "revenue change"}],
        "MetricSpec": [{"metric_name": "revenue", "kind": "total", "order_value_sql": "SUM(op.payment_value)",
                        "joins": ["order_payments"], **APRIL_VS_MARCH}],
        "Narrative": [NARRATIVE],
    }
    result = run_question("Why did revenue jump in April 2018?", "olist", _deps(con, replies), save=False)

    top = result["report"]["evidence"]["top_candidates"][0]
    assert (top["dimension"], top["segment"]) == ("data_quality", "order_payments")
    assert result["report"]["evidence"]["data_quality_findings"][0]["duplicate_rate_b"] > 0.4


def test_bad_metric_sql_is_retried_with_the_error_message():
    con = fake_olist.build()
    replies = {
        "Route": [{"intent": "why_change", "reason": "rate change"}],
        "MetricSpec": [
            {"metric_name": "late rate", "kind": "per_order_average", "order_value_sql": "MAX(o.no_such_column)", **APRIL_VS_MARCH},
            {"metric_name": "late rate", "kind": "per_order_average",
             "order_value_sql": "MAX(CASE WHEN o.order_delivered_customer_date > o.order_estimated_delivery_date THEN 1 ELSE 0 END)",
             **APRIL_VS_MARCH},
        ],
        "Narrative": [NARRATIVE],
    }
    deps = _deps(con, replies)
    result = run_question("Why did the late delivery rate change?", "olist", deps, save=False)

    assert result["status"] in {"ok", "insufficient_evidence", "no_significant_change"}
    assert result["queries"][0]["error"]  # first attempt failed and was logged in the audit trail
    retry_prompt = [p for name, p in deps.llm.prompts if name == "MetricSpec"][1]
    assert "previous attempt failed" in retry_prompt


def test_data_question_rejects_unsafe_sql_then_answers():
    con = fake_olist.build()
    replies = {
        "Route": [{"intent": "data_question", "reason": "asks for a count"}],
        "SQLDraft": [
            {"purpose": "count orders", "sql": "DELETE FROM olist.orders"},
            {"purpose": "count orders", "sql": "SELECT COUNT(*) AS n FROM olist.orders"},
        ],
        "Answer": [{"answer": "There are 400 orders [Q2]."}],
    }
    result = run_question("How many orders are there?", "olist", _deps(con, replies), save=False)

    assert result["status"] == "ok"
    assert "Rejected by validator" in result["queries"][0]["error"]
    assert result["queries"][1]["row_count"] == 1
    assert con.execute("SELECT COUNT(*) FROM olist.orders").fetchone()[0] > 0  # nothing was deleted


def test_hallucinated_number_in_answer_is_flagged():
    con = fake_olist.build()
    replies = {
        "Route": [{"intent": "data_question", "reason": "count"}],
        "SQLDraft": [{"purpose": "count orders", "sql": "SELECT COUNT(*) AS n FROM olist.orders"}],
        "Answer": [{"answer": "There are 98765 orders [Q1]."}],
    }
    result = run_question("How many orders?", "olist", _deps(con, replies), save=False)
    assert "98765" in result["report"]["unsupported_numbers"]


def test_unanswerable_question_is_refused_without_queries():
    con = fake_olist.build()
    replies = {"Route": [{"intent": "unanswerable", "reason": "no website traffic data"}]}
    result = run_question("Why did website traffic drop?", "olist", _deps(con, replies), save=False)
    assert result["status"] == "unanswerable"
    assert result["queries"] == []
