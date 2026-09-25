# 02 Risk assessment: AI-specific hazards (GAMP 5 functional risk assessment + CSA)

Severity (S) and probability (P) on 1–3, detectability (D) 1 = certain detection, 3 = unlikely. RPN = S × P × D.
**RPN ≥ 12 → scripted testing with negative cases; lower → unscripted/exploratory testing (CSA).**
Every control listed exists in the code; the last column is the evidence.

| # | Hazard | Effect in a quality investigation | S | P | D | RPN | Control | Evidence |
|---|---|---|---|---|---|---|---|---|
| R1 | LLM invents a number | Investigation chases a change that doesn't exist | 3 | 2 | 3 | **18** | Grounding check: every number in the answer must appear in query results, else flagged and shown as a warning | `test_invented_number_is_flagged`, `test_hallucinated_number_in_answer_is_flagged`; benchmark: 0% unsupported numbers (50 questions) |
| R2 | Wrong SQL gives a wrong number | Wrong conclusion that looks well-supported | 3 | 2 | 2 | **12** | Metrics come from a reviewed semantic layer, not free-form SQL; SQL errors are retried with the error; every number cites its query id | `test_bad_metric_sql_is_retried_with_the_error_message`; benchmark SQL accuracy 100% |
| R3 | Agent modifies GxP data | Loss of data integrity in the source | 3 | 1 | 3 | 9 | SQL validator (SELECT only, schema allow-list, CTE checks) + read-only database role (second, independent layer) | `test_unsafe_queries_are_rejected` (DELETE, DROP, CTE-hidden DELETE, pg_sleep); read-only role write test |
| R4 | A data bug is reported as a real business change | Wrong root cause (e.g. duplicated records read as a real spike) | 3 | 2 | 2 | **12** | Data-quality checks (duplicate rates) run before blaming the process | `test_duplicate_payment_rows_are_reported_as_data_quality_issue`; benchmark rc13–rc15 |
| R5 | Answers a question the data can't answer | False confidence | 2 | 2 | 2 | 8 | Router refuses unanswerable questions; no queries run | `test_unanswerable_question_is_refused_without_queries`; benchmark 100% correct refusals |
| R6 | Stored answer or its SQL is edited later | Evidence in an investigation no longer matches what was shown | 3 | 1 | 3 | 9 | **v1.2:** hash-chained audit log + re-read of every run on verification | `tests/test_audit_log.py` (7 tests: edited answer, edited SQL, deleted run, rewritten or removed log entry, run inserted outside the app) |
| R7 | Provider silently changes the model | Accuracy drops with no code change | 3 | 2 | 3 | **18** | Model pinned in config; model recorded per answer; **change control: benchmark must pass before a new model is accepted** | `evals/reports/latest.json` records the model; procedure in 04 |
| R8 | Answer cannot be attributed (who asked, which model, when) | Fails ALCOA+ *Attributable* | 2 | 2 | 2 | 8 | Run stores question, time (UTC), model; v1.2 audit log. **Gap:** no user identity yet (single-user demo) | Open item G1 below |
| R9 | Prompt injection through retrieved documents | Agent follows instructions hidden in a document | 2 | 1 | 3 | 6 | Documents are only cited as context; the agent can only run validated SELECTs, so the worst case is a wrong *candidate*, caught by review | SQL validator tests; human review (intended use) |

## Open gaps (must close before real GxP use)
| ID | Gap | Proposed fix |
|---|---|---|
| G1 | No user login, so questions aren't attributable to a person | SSO in front of the app; store the user id in `runs` and in each audit entry |
| G2 | Audit log sequence is assigned in the application | Database sequence + append-only permissions (no UPDATE/DELETE grant) on `audit_log` |
| G3 | No periodic review of the audit trail | Monthly `GET /audit/verify` with the result filed in the QMS |
| G4 | LLM provider is an external supplier | Supplier assessment and a data-processing agreement before any real data is sent |
