from pathlib import Path

from backend.agent.graph import AgentDeps
from backend.agent.runner import run_question
from backend.llm import ScriptedLLM
from backend.rag.chunking import chunk_documents, chunk_text
from backend.rag.embeddings import HashingEmbedder
from backend.rag.store import InMemoryDocStore
from tests import fake_olist

CORPUS = Path(__file__).resolve().parents[1] / "docs" / "ops_corpus" / "olist_lab"


def test_chunk_text_keeps_paragraphs_and_respects_size():
    body = "\n\n".join(["a" * 400, "b" * 400, "c" * 400])
    chunks = chunk_text(body, max_chars=900)
    assert chunks == ["a" * 400 + "\n\n" + "b" * 400, "c" * 400]


def test_corpus_parses_with_dates_and_types():
    chunks = chunk_documents(CORPUS)
    ids = {c.doc_id for c in chunks}
    assert "2018-06-04_incident_carrier_sp" in ids
    carrier = next(c for c in chunks if c.doc_id == "2018-06-04_incident_carrier_sp")
    assert carrier.doc_type == "incident" and carrier.doc_date == "2018-06-04"


def _store() -> InMemoryDocStore:
    store = InMemoryDocStore(HashingEmbedder())
    store.ingest("olist_lab", chunk_documents(CORPUS))
    return store


def test_hybrid_search_finds_the_matching_incident():
    hits = _store().search("late delivery rate customer_state SP", "olist_lab", "2018-06-01", "2018-07-01")
    assert hits[0]["doc_id"] == "2018-06-04_incident_carrier_sp"


def test_date_window_excludes_documents_from_other_periods():
    hits = _store().search("duplicate payment rows revenue", "olist_lab", "2018-06-01", "2018-07-01", k=10)
    assert all(h["doc_id"] != "2017-11-06_incident_duplicate_payments" for h in hits)


def test_agent_attaches_related_documents_to_the_report():
    con = fake_olist.build(drop_state="MG")
    store = _store()
    replies = {
        "Route": [{"intent": "why_change", "reason": "orders dropped"}],
        "MetricSpec": [{"metric_name": "orders", "kind": "total", "order_value_sql": "1",
                        "date_column": "order_purchase_timestamp",
                        "period_a_start": "2018-03-01", "period_a_end": "2018-04-01",
                        "period_b_start": "2018-04-01", "period_b_end": "2018-05-01"}],
        "Narrative": [{"summary": "s", "root_cause_explanation": "e", "next_checks": ["c"], "suggested_experiment": "x"}],
    }
    deps = AgentDeps(llm=ScriptedLLM(replies), run_sql=fake_olist.runner_for(con), schema_context=fake_olist.context,
                     retrieve=lambda q, ds, s, e: store.search(q, "olist_lab", s, e, k=3))
    result = run_question("Why did orders drop in April 2018?", "olist", deps, save=False)
    docs = result["report"]["evidence"]["related_documents"]
    assert docs and docs[0]["doc_ref"] == "D1"
    assert "2018-04-03_ops_mg_warehouse" in {d["doc_id"] for d in docs}
