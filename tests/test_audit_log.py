"""Tamper-evident audit log (21 CFR Part 11 §11.10(e), ALCOA+): edits outside the app must be detected."""

import pytest
from sqlalchemy import create_engine, event, text

from backend.db import app_store

S = app_store.APP_SCHEMA


@pytest.fixture
def store(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    path = (tmp_path / "app.sqlite").as_posix()

    @event.listens_for(engine, "connect")
    def _attach(dbapi_conn, _record):
        dbapi_conn.execute(f"ATTACH DATABASE '{path}' AS {S}")

    monkeypatch.setattr(app_store, "DEMO_MODE", True)
    monkeypatch.setattr(app_store, "admin_engine", lambda: engine)
    app_store.init_app_tables()
    yield engine
    engine.dispose()


def _result(question="Why did orders drop in April 2018?", status="ok", answer="Orders fell 18% [Q1]."):
    return {"question": question, "dataset": "olist_lab", "status": status,
            "report": {"type": "root_cause", "answer": answer},
            "queries": [{"query_id": "Q1", "purpose": "orders by month", "sql_submitted": "SELECT 1",
                         "sql_executed": "SELECT 1 LIMIT 1000", "row_count": 2, "duration_ms": 5, "preview": [[1]]}],
            "usage": {"models": ["gemini/gemini-3.6-flash"]}, "duration_s": 12.3}


def _sql(engine, statement: str, **params):
    with engine.begin() as conn:
        conn.execute(text(statement), params)


def test_untouched_trail_verifies_and_records_the_model(store):
    run_id = app_store.save_run(_result())
    app_store.add_feedback(run_id, 1, "useful")
    result = app_store.verify_audit()
    assert result == {"intact": True, "entries": 2, "problems": []}
    newest, oldest = app_store.audit_log()
    assert (oldest["event"], newest["event"]) == ("run_recorded", "feedback")
    assert oldest["payload"]["models"] == ["gemini/gemini-3.6-flash"] and oldest["prev_hash"] == app_store.GENESIS
    assert newest["prev_hash"] == oldest["hash"]


def test_editing_an_answer_directly_in_the_database_is_detected(store):
    run_id = app_store.save_run(_result())
    _sql(store, f"UPDATE {S}.runs SET report = :r WHERE run_id = :id",
         r='{"type": "root_cause", "answer": "Orders fell 5% [Q1]."}', id=run_id)
    result = app_store.verify_audit()
    assert not result["intact"]
    assert result["problems"][0]["problem"] == "run or its queries changed after they were recorded"


def test_editing_the_executed_sql_is_detected(store):
    run_id = app_store.save_run(_result())
    _sql(store, f"UPDATE {S}.queries SET sql_executed = 'SELECT 2' WHERE run_id = :id", id=run_id)
    assert not app_store.verify_audit()["intact"]


def test_deleting_a_run_is_detected(store):
    run_id = app_store.save_run(_result())
    _sql(store, f"DELETE FROM {S}.queries WHERE run_id = :id", id=run_id)
    _sql(store, f"DELETE FROM {S}.runs WHERE run_id = :id", id=run_id)
    assert app_store.verify_audit()["problems"][0]["problem"] == "run deleted"


def test_rewriting_or_removing_audit_entries_breaks_the_chain(store):
    app_store.save_run(_result())
    second = app_store.save_run(_result(question="Why did revenue jump?"))
    app_store.save_run(_result(question="How many orders were canceled?"))
    _sql(store, f"UPDATE {S}.audit_log SET payload = replace(payload, 'revenue', 'profit') WHERE run_id = :id",
         id=second)
    assert {p["seq"] for p in app_store.verify_audit()["problems"]} == {2}
    _sql(store, f"DELETE FROM {S}.audit_log WHERE seq = 2")
    problems = app_store.verify_audit()["problems"]
    assert any(p.get("seq") == 3 for p in problems)                       # the next entry no longer links
    assert any(p.get("run_id") == second and "no audit entry" in p["problem"] for p in problems)


def test_run_inserted_outside_the_app_is_reported(store):
    _sql(store, f"INSERT INTO {S}.runs (run_id, question, dataset, status, report, usage, created_at) "
                "VALUES ('x-1', 'q', 'olist', 'ok', '{}', '{}', '2026-01-01')")
    assert app_store.verify_audit()["problems"] == [
        {"run_id": "x-1", "problem": "run has no audit entry (inserted outside the app?)"}]


def test_runs_saved_before_the_audit_log_are_baselined_once(store):
    _sql(store, f"INSERT INTO {S}.runs (run_id, question, dataset, status, report, usage, created_at) "
                "VALUES ('legacy-1', 'q', 'olist', 'ok', '{}', '{}', '2026-01-01')")
    app_store.init_app_tables()
    app_store.init_app_tables()                                            # idempotent: no second baseline
    log = app_store.audit_log()
    assert [e["event"] for e in log] == ["run_baselined"]
    assert app_store.verify_audit()["intact"]


def test_model_change_gate_accepts_the_current_report_and_rejects_a_worse_one():
    from evals.check_thresholds import check
    good = {"sql_execution_accuracy_pct": 100, "root_cause_hit_at_1_pct": 93.3, "correct_refusal_pct": 100,
            "answers_with_unsupported_numbers_pct": 0}
    assert all(r[-1] for r in check(good))
    worse = {**good, "root_cause_hit_at_1_pct": 80.0, "answers_with_unsupported_numbers_pct": 4.0}
    assert [r[0] for r in check(worse) if not r[-1]] == ["Root-cause Hit@1", "Answers with unsupported numbers"]
