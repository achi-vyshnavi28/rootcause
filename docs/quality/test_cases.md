# Test-case library (manual / UAT) v1.2

Manual cases for UAT and demos. Automated counterparts are listed where they exist. Environment: local PostgreSQL 16 with `olist` + `olist_lab`, Streamlit UI, Gemini free tier.

| ID | Title | Preconditions | Steps | Expected result | Automated? |
|---|---|---|---|---|---|
| TC01 | Root cause: order drop | Lab data loaded | 1. Select "Olist lab" 2. Ask "Why did the number of orders drop in April 2018 compared to March 2018?" | Status ok; headline shows orders March → April with % change; top candidate customer_state = MG; citations [Q#] present | rc01 |
| TC02 | Root cause: ratio metric | Lab data | Ask "Why did the late delivery rate increase in June 2018 compared to May 2018?" | Metric shown as a rate (3 decimals); top candidate customer_state = SP; carrier incident cited [D#] | rc04 |
| TC03 | Data bug detection | Lab data | Ask "Why did revenue jump in October 2017 compared to September 2017?" | Red data-quality banner (order_payments duplicates 0% → ~29%); summary says data problem; ETL incident cited | rc13 |
| TC04 | Plain data question | Original data | Select "Olist (original)"; ask "How many orders were canceled?" | Answer 625 with [Q1]; one query in the audit trail | sql17 |
| TC05 | Refusal | Any | Ask "Why did website traffic drop?" | Status unanswerable; no queries run | rf01 |
| TC06 | Audit trail | Run TC01 | Expand "Audit trail" | Every query shows purpose, SQL, row count, time and preview; no errors | – |
| TC07 | Unsafe SQL blocked | pytest | Run `pytest tests/test_sql_validator.py` | All unsafe queries rejected (DELETE, DROP, CTE-DELETE, pg_sleep, other schemas) | yes |
| TC08 | Read-only role | DB set up | Run `python -m data.setup_readonly_role` | "Write test passed: DELETE was refused." | yes |
| TC09 | Feedback | Run any question | Click 👍 | Toast "Thanks!"; a row in `rootcause_app.feedback` | – |
| TC10 | History | Several runs | Open History tab | Runs listed newest first with status and duration | – |
| TC11 | Evals tab | Benchmark run | Open Evals tab | Summary metrics and per-question results displayed without errors | – |
| TC12 | Provider failure | Set an invalid `LLM_MODEL` in `.env` | Ask any question | Status error with a readable message; app does not crash | – |
| TC13 | Webhook duplicate | Integrations service | Post the same signed Razorpay event twice | 202 then 200 `{"duplicate": true}`; one event stored | yes (03) |
| TC14 | Dead-letter replay | Integrations service | Force a handler error until dead-lettered; fix; `replay_events --dead-letter` | Event processed; order state correct | yes (08) |
| TC15 | Anomaly API | API running | `GET /anomalies?dataset=olist_lab` | Includes 2018-08 canceled_rate spikes and 2017-11-24 order spike | – |
| TC16 | Audit trail intact (v1.2) | Some runs saved | Open History tab | Green banner "Audit trail intact: N hash-chained entries verified" | Playwright `test_history_tab_verifies_the_audit_trail`; Postman 12 |
| TC17 | Tampering detected (v1.2) | Run TC04; DB admin access | In SQL, `UPDATE rootcause_app.runs SET report = ... WHERE run_id = '<id>'`; open History tab | Red banner "Audit trail problem: 1 issue(s)"; the table names the run and "changed after they were recorded" | `tests/test_audit_log.py` (7 cases) |
| TC18 | Model recorded per answer (v1.2) | Run TC04 | `GET /runs/<id>`; `GET /audit/log?limit=2` | `usage.models` lists the model; the audit entry for the run carries the same model | Postman 06, 11 |
| TC19 | Legacy runs baselined once (v1.2) | Database with runs from before v1.2 | Start the app twice; `GET /audit/log` | One `run_baselined` entry per legacy run, not two; `/audit/verify` intact | `test_runs_saved_before_the_audit_log_are_baselined_once` |
| TC20 | Model change control (v1.2) | New model id proposed | Set `LLM_MODEL`; run `python -m evals.run_evals`; compare with thresholds in `docs/gxp/04` | Accept only if SQL ≥ 95%, Hit@1 ≥ 85%, refusals 100%, unsupported numbers ≤ 2% | Postman 13 checks the thresholds on the latest report |

## Bug report template
```
Title: <component>: <short symptom>
Environment: <branch/commit, dataset, model>
Steps to reproduce: 1. 2. 3.
Expected: ...
Actual: ...   (attach run_id and screenshot)
Severity: S1 blocker / S2 major / S3 minor / S4 cosmetic
Evidence: audit trail query ids, logs
```

## Regression sweep (before each release)
`python -m pytest` (all green) → `pytest tests_ui` (Playwright, screenshots in `docs/quality/ui_evidence/`) → Newman run of `postman/` (all assertions pass) → `GET /audit/verify` intact → `python -m evals.run_evals --limit 2` (no metric below the last release) → TC01-TC06 manually in the UI.

Real defects found so far are logged in `bug_reports.md`.
