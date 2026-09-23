# User stories, acceptance criteria and traceability

Each story maps to requirements (PRD F#, BRD BR#) and to the tests that verify it.

| ID | Story | Acceptance criteria (Given / When / Then) | Req | Verified by |
|---|---|---|---|---|
| US1 | As an ops manager, I want to ask "why did orders drop in April?" so I get the cause without waiting for an analyst. | Given the lab data with the MG drop, when I ask the question, then the top candidate is customer_state = MG with its share of the change and a query id. | F1-F3, BR1 | `tests/test_agent.py::test_order_drop_is_traced_to_the_planted_state`; benchmark rc01-rc03 |
| US2 | As a finance analyst, I want revenue jumps caused by data bugs flagged as data problems so we don't celebrate fake growth. | Given duplicated payment rows, when I ask why revenue jumped, then the first candidate is data_quality / order_payments with the duplicate rates. | F5, BR3 | `test_duplicate_payment_rows_are_reported_as_data_quality_issue`; rc13-rc15 |
| US3 | As a data lead, I want every number in an answer to link to its SQL so I can audit it. | Given any report, then each query id cited exists in the audit trail with executed SQL, row count and preview. | F6, BR2 | audit trail in UI/API `/runs/{id}/audit` |
| US4 | As a data lead, I want invented numbers flagged. | Given an answer containing a number not in the evidence, then it appears in `unsupported_numbers` and the UI shows a warning. | F7 | `test_hallucinated_number_in_answer_is_flagged`; `tests/test_grounding.py` |
| US5 | As the platform owner, I want the agent unable to change data. | Given a DELETE/UPDATE/DROP (also hidden inside a CTE), then the validator rejects it; given a bypass, then the read-only role refuses it. | F8, BR4 | `tests/test_sql_validator.py`; `data/setup_readonly_role.py` write test |
| US6 | As a manager, I want the agent to say when it can't answer. | Given a question about data that doesn't exist (web traffic), then status = unanswerable and no queries run. | BR6 | `test_unanswerable_question_is_refused_without_queries`; rf01-rf05 |
| US7 | As an analyst, I want related incidents and releases shown with the cause. | Given the SP late-delivery spike, then the carrier incident document is attached as [D#]. | F9 | `tests/test_rag.py` |
| US8 | As an analyst, I want SQL errors fixed automatically. | Given a metric definition that errors, then the agent retries with the error message (max 3) and logs the failed attempt. | F1 | `test_bad_metric_sql_is_retried_with_the_error_message` |
| US9 | As an ops manager, I want to test a fix before rolling it out. | Given the capacity-loss scenario, when a second carrier is simulated, then the late rate and backlog are reported for each start day. | F12 | `tests/test_optimization.py` |
| US10 | As a support engineer, I want duplicate or out-of-order webhooks handled safely. | Given the same event twice or events out of order, then state is updated once and never goes backwards. | (integrations) | `integrations/integration_tests/test_webhooks.py` 03-04 |

## Definition of done
Code reviewed; tests added and passing in CI; benchmark not regressed; decision log updated when a design choice was made; README/runbook updated.
