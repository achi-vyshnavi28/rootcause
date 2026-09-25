"""Build the Postman collection for the RootCause API (python postman/build_collection.py).

Kept as code so each request and its assertions are reviewable in one place; the JSON is generated.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def req(name, method, path, tests, body=None, pre=None):
    item = {"name": name,
            "request": {"method": method, "header": [{"key": "Content-Type", "value": "application/json"}] if body else [],
                        "url": {"raw": "{{baseUrl}}" + path, "host": ["{{baseUrl}}"],
                                "path": [p for p in path.split("?")[0].split("/") if p],
                                **({"query": [{"key": k, "value": v} for k, v in
                                              (q.split("=") for q in path.split("?")[1].split("&"))]}
                                   if "?" in path else {})}},
            "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": tests}}]}
    if body is not None:
        item["request"]["body"] = {"mode": "raw", "raw": json.dumps(body, indent=1)}
    if pre:
        item["event"].append({"listen": "prerequest", "script": {"type": "text/javascript", "exec": pre}})
    return item


def T(name: str, body: str) -> str:
    return f"pm.test({name!r}, () => {{ {body}; }});"

items = [
    req("01 Health", "GET", "/health", [
        T("200 OK", "pm.response.to.have.status(200)"),
        T("reports the pinned model", "pm.expect(pm.response.json().model).to.match(/^gemini\\//)")]),
    req("02 Datasets", "GET", "/datasets", [
        T("both datasets listed", "pm.expect(pm.response.json()).to.have.keys('olist', 'olist_lab')")]),
    req("03 Ask: question too short is rejected", "POST", "/ask", [
        T("422 validation error", "pm.response.to.have.status(422)"),
        T("error names the question field", "pm.expect(JSON.stringify(pm.response.json().detail)).to.include('question')")],
        body={"question": "hi", "dataset": "olist"}),
    req("04 Ask: unknown dataset is rejected before any LLM call", "POST", "/ask", [
        T("400 Bad Request", "pm.response.to.have.status(400)"),
        T("message lists valid datasets", "pm.expect(pm.response.json().detail).to.include('olist_lab')")],
        body={"question": "How many orders were canceled?", "dataset": "production_db"}),
    req("05 Ask: data question with a known answer", "POST", "/ask", [
        T("200 OK", "pm.response.to.have.status(200)"),
        "const r = pm.response.json(); pm.collectionVariables.set('runId', r.run_id);",
        T("status ok", "pm.expect(r.status).to.eql('ok')"),
        T("answer gives the true count (625)", "pm.expect(r.report.answer).to.include('625')"),
        T("answer cites its query", "pm.expect(r.report.answer).to.match(/\\[Q\\d+\\]/)"),
        T("no unsupported numbers", "pm.expect(r.report.unsupported_numbers || []).to.be.empty"),
        T("every query was validated (executed SQL has a LIMIT)",
          "r.queries.filter(q => q.sql_executed).forEach(q => pm.expect(q.sql_executed).to.match(/LIMIT/i))")],
        body={"question": "How many orders were canceled?", "dataset": "olist"}),
    req("06 Stored run matches what was returned", "GET", "/runs/{{runId}}", [
        T("200 OK", "pm.response.to.have.status(200)"),
        T("same question and dataset", "pm.expect(pm.response.json()).to.include({question: 'How many orders were canceled?', dataset: 'olist'})"),
        T("model recorded for the answer", "pm.expect(pm.response.json().usage.models).to.not.be.empty")]),
    req("07 Query audit trail for the run", "GET", "/runs/{{runId}}/audit", [
        T("at least one query", "pm.expect(pm.response.json().length).to.be.above(0)"),
        T("each query has SQL and a row count or an error",
          "pm.response.json().forEach(q => { pm.expect(q.sql_submitted).to.be.a('string'); "
          "pm.expect(q.row_count !== null || q.error !== null).to.be.true; })")]),
    req("08 Feedback: rating out of range is rejected", "POST", "/runs/{{runId}}/feedback", [
        T("422 validation error", "pm.response.to.have.status(422)")], body={"rating": 5}),
    req("09 Feedback: valid rating is saved", "POST", "/runs/{{runId}}/feedback", [
        T("200 OK and saved", "pm.response.to.have.status(200); pm.expect(pm.response.json().saved).to.be.true")],
        body={"rating": 1, "comment": "Postman regression run"}),
    req("10 Unknown run returns 404", "GET", "/runs/00000000-0000-0000-0000-000000000000", [
        T("404 Not Found", "pm.response.to.have.status(404)")]),
    req("11 Audit log is hash-chained", "GET", "/audit/log?limit=5", [
        "const log = pm.response.json();",
        T("newest entry is this run's feedback",
          "pm.expect(log[0]).to.include({event: 'feedback', run_id: pm.collectionVariables.get('runId')})"),
        T("previous entry is this run being recorded", "pm.expect(log[1].event).to.eql('run_recorded')"),
        T("entries are linked by hash", "pm.expect(log[0].prev_hash).to.eql(log[1].hash)"),
        T("hashes are SHA-256", "pm.expect(log[0].hash).to.match(/^[0-9a-f]{64}$/)")]),
    req("12 Audit verify: trail intact", "GET", "/audit/verify", [
        T("200 OK", "pm.response.to.have.status(200)"),
        T("intact, no problems", "pm.expect(pm.response.json()).to.include({intact: true}); "
                                 "pm.expect(pm.response.json().problems).to.be.empty")]),
    req("13 Latest benchmark report", "GET", "/evals/latest", [
        "const s = pm.response.json().summary;",
        T("50 questions", "pm.expect(s.questions).to.eql(50)"),
        T("no invented numbers", "pm.expect(s.answers_with_unsupported_numbers_pct).to.eql(0)"),
        T("meets the model change-control thresholds",
          "pm.expect(s.sql_execution_accuracy_pct).to.be.at.least(95); "
          "pm.expect(s.root_cause_hit_at_1_pct).to.be.at.least(85); pm.expect(s.correct_refusal_pct).to.eql(100)")]),
]

collection = {
    "info": {"name": "RootCause API",
             "description": "Regression suite: input validation, a known-answer question, grounding, stored runs, "
                            "feedback, the hash-chained audit log and the benchmark thresholds used for model change control.",
             "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
    "variable": [{"key": "runId", "value": ""}],
    "item": items,
}
env = {"name": "RootCause local", "values": [{"key": "baseUrl", "value": "http://localhost:8700", "enabled": True}]}
(HERE / "RootCause.postman_collection.json").write_text(json.dumps(collection, indent=2), encoding="utf-8")
(HERE / "local.postman_environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")
print(f"{len(items)} requests, {sum(sum(line.startswith('pm.test') for line in i['event'][0]['script']['exec']) for i in items)} assertions")
