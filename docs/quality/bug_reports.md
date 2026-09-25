# Bug reports

Real defects found while building and testing v1.2, in the template from `test_cases.md`.
Severity: S1 blocker · S2 major · S3 minor · S4 cosmetic.

---

## BUG-001: UI: "Not helpful" feedback button label is cut off
| | |
|---|---|
| Found | 2026-09-25, reviewing Playwright evidence screenshot `02_answer_with_audit_trail.png` |
| Environment | main @ v1.2 work, Streamlit 1.x, Chromium 153, viewport 1400 × 900 |
| Severity | S4 cosmetic (but a feedback control users can't read gets used less, which weakens the "trusted" metric in the PRD) |

**Steps to reproduce**
1. Open the app at 1400 px width. 2. Ask "How many orders were canceled?" on *Olist e-commerce (original)*.
3. Look at the two feedback buttons under the answer.

**Expected:** both labels fully visible: "👍 Helpful", "👎 Not helpful".
**Actual:** the second button reads "👎 Not hel…".
**Root cause:** feedback buttons sit in columns with ratio `[1, 1, 6]`; the second column is narrower than its label.
**Fix:** ratio `[1, 1.5, 5]` (`frontend/app.py`).
**Regression test:** `tests_ui/test_streamlit_ui.py::test_known_answer_question_is_answered_with_evidence` now checks
that no button text overflows. Verified it **fails on the old layout and passes on the fix**.
**Status:** Closed.

---

## BUG-002: API: every question fails with `ImportError: DLL load failed`
| | |
|---|---|
| Found | 2026-09-25, Postman/Newman regression run, request 05 (5 of 30 assertions failed) |
| Environment | Windows 11 dev laptop with Windows Application Control; PostgreSQL 16; gemini-3.6-flash |
| Severity | S1 blocker: no question can be answered; the API still returns 200 with `status: error`, so only a content check catches it |

**Steps to reproduce**
1. `uvicorn backend.api.main:app --port 8700`. 2. `POST /ask {"question": "How many orders were canceled?", "dataset": "olist"}`.

**Expected:** `status: ok`, answer contains 625 with a query citation.
**Actual:** `status: error`, answer `ImportError: DLL load failed while importing _tiktoken: An Application Control policy has blocked this file.`
**Root cause:** Windows Application Control started blocking compiled files in the newest releases of three
dependencies: `tiktoken` 0.14 (via LiteLLM), `xxhash` 4.0 (via LangGraph's tracing library) and `statsmodels` 0.15.
No code changed; the environment did.
**Fix:** pinned `tiktoken==0.9.0`, `xxhash==3.6.0`, `statsmodels==0.14.5` (all load), recorded in `requirements.txt`
and decision log #10. The security policy was left as it is.
**Verification:** Newman re-run 13/13 requests, 30/30 assertions; `pytest` 95 passed.
**Lesson:** the API answering 200 hid a total failure. The Postman suite asserts on *content* (the true answer),
not only status codes, which is what caught it.
**Status:** Closed.

---

## BUG-003: Test: UI evidence screenshot taken before the audit trail had opened
| | |
|---|---|
| Found | 2026-09-25, reviewing the first Playwright evidence screenshots |
| Severity | S3 (test defect): the test passed, but its evidence did not show what the test claimed |

**Actual:** the screenshot showed the "Audit trail" expander header but not the SQL inside it, although the test
had asserted the SQL was visible.
**Root cause:** the check `get_by_text("LIMIT").first` could match before the expander finished opening, and the
screenshot was taken immediately after.
**Fix:** assert on the SQL code block itself (contains `LIMIT` and `canceled`) and wait for the expander to finish
before the screenshot. The new screenshot shows question, answer, validated SQL and result row.
**Why it matters:** in validation, evidence that doesn't show the claimed result is a finding, even when the test passed.
**Status:** Closed.
