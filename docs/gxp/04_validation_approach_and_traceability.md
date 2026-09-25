# 04 Validation approach (CSA) and traceability

## Approach
Risk-based, following FDA CSA and GAMP 5 (2nd edition): effort goes where the risk assessment (02) says patient or
data-integrity risk is high. Most of the evidence is automated and repeatable, so it can be re-run for every change.

| Level | What it proves | Evidence | Result |
|---|---|---|---|
| Unit / functional (OQ-like) | Each control works, including negative cases | `pytest` suite (grounding, SQL validator, agent, audit log) | All pass in CI |
| **Performance benchmark (PQ-like)** | The whole system gives right answers on realistic questions | 50 questions with known answers, incl. planted root causes and unanswerable questions (`evals/`) | 100% SQL accuracy, 93.3% root-cause Hit@1, 100% Hit@3, 100% correct refusals, 0% unsupported numbers |
| Exploratory (unscripted) | Behaviour a script didn't anticipate | Manual sessions recorded in the test library | See `docs/quality/test_library_v1.2.xlsx` |

## Requirements for GxP use → evidence
| ID | Requirement | Risk | Verified by | Status |
|---|---|---|---|---|
| GR-01 | Every number in an answer is supported by a stored query result | R1 | `test_invented_number_is_flagged`, `test_hallucinated_number_in_answer_is_flagged`, benchmark | Pass |
| GR-02 | The system cannot change source data | R3 | `test_unsafe_queries_are_rejected`, read-only role write test | Pass |
| GR-03 | Data-quality problems are reported before business causes | R4 | `test_duplicate_payment_rows_are_reported_as_data_quality_issue`, rc13–rc15 | Pass |
| GR-04 | Unanswerable questions are refused without running queries | R5 | `test_unanswerable_question_is_refused_without_queries`, rf01–rf05 | Pass |
| GR-05 | Every stored answer is tamper-evident: edits, deletions and insertions outside the app are detected | R6 | `tests/test_audit_log.py` (7 tamper tests), Postman 11-12, Playwright History tab | Pass |
| GR-06 | Each answer records the model that produced it | R7, R8 | `test_untouched_trail_verifies_and_records_the_model` | Pass |
| GR-07 | Answers existing before the audit log are baselined once and then protected | R6 | `test_runs_saved_before_the_audit_log_are_baselined_once`; production database: 64 runs baselined, chain intact | Pass |
| GR-08 | A model change is accepted only if the benchmark meets the acceptance criteria | R7 | Automated gate `python -m evals.check_thresholds` (exit 1 = reject), `test_model_change_gate_accepts_the_current_report_and_rejects_a_worse_one`, Postman 13 | Pass |
| GR-09 | Each question is attributable to a named user | R8 | Not implemented | **Open (G1)** |

## Model change control (the AI-specific procedure)
A new model or model version is a change to a validated system, even though no code changes.
1. Raise a change request stating the old and new model ids and the reason.
2. Run `python -m evals.run_evals` with the new model, then `python -m evals.check_thresholds` (the gate). **Acceptance:** SQL accuracy ≥ 95%, root-cause Hit@1 ≥ 85%,
   correct refusals = 100%, unsupported numbers ≤ 2%, and no question that passed before now fails without explanation.
3. Review failures one by one (see `docs/decision_log.md` #13 for how scoring errors vs real errors were separated).
4. Approve, then update `LLM_MODEL`; the audit log records the new model on every answer from then on.

Why this matters in practice: during development the provider retired the Gemini model RootCause was first written
against, with no code change on our side (decision log #14). That happened before the benchmark existed; this
procedure is what would catch the same event in a validated deployment.
