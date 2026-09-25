# PRD v1.2: GxP readiness (trustworthy answers for regulated teams)

| | |
|---|---|
| Status | RC-121 to RC-124 built and verified; RC-125 and RC-126 planned |
| Owner | Vyshnavi Achi |
| Date | 2026-09-25 |
| Inputs | `docs/gxp/01-04` (intended use, risk assessment, ALCOA+, validation approach) |

## Problem
A quality team investigating a rise in deviations could use RootCause to find where to look first. But in a GxP
setting an answer is only useful if an auditor can later check it: who asked, which model answered, what SQL produced
each number, and proof that none of it changed afterwards. v1 stored runs, but anyone with database access could edit
an answer without a trace, and the model behind an answer was not recorded.

## Goals and success metrics
| Goal | Metric | Target | Result |
|---|---|---|---|
| Stored answers are tamper-evident | Tampering scenarios detected (edit answer, edit SQL, delete run, rewrite or remove log entry, insert run outside the app) | 5 of 5 | 5 of 5 (`tests/test_audit_log.py`) |
| Every answer is attributable to a model | Stored answers with the model recorded | 100% | 100% for new runs |
| Model changes don't silently lower quality | Model changes accepted without passing the benchmark gate | 0 | Gate automated |
| No regression | 50-question benchmark | ≥ v1 on every metric | Unchanged (no agent change) |

**Non-goals:** electronic signatures (they belong in the QMS, see `docs/gxp/01` §3); making RootCause a system of record.

## User stories

### RC-121 Tamper-evident answer log
As a QA auditor, I want every stored answer protected by a hash chain, so I can prove an investigation's evidence was not changed after the fact.
- When a run is saved, the system appends an audit entry with a SHA-256 digest of the question, answer, executed SQL, row counts and model, linked to the previous entry's hash.
- `GET /audit/verify` recomputes the chain and re-reads every run; it reports each run that was edited, deleted or inserted outside the app.
- The History tab shows "Audit trail intact" in green, or the list of problems in red.
- Audit entries are never updated or deleted by the application.

### RC-122 Model recorded per answer
As a QA auditor, I want each answer to record the model that produced it, so a change in behaviour can be traced to a model change.
- Each stored run lists the model id(s) used.
- The audit entry for the run contains the same model id(s).
- A run that failed before any model call is stored with status `error` and an empty model list, so it is not mistaken for a model's answer.

### RC-123 Baseline answers saved before v1.2
As the system owner, I want runs saved before the audit log existed to be baselined once, so history is protected from go-live without pretending it was always protected.
- On start-up, the system gives each run without an audit entry exactly one `run_baselined` entry.
- Starting the app again adds no further entries.
- `GET /audit/verify` checks baselined runs the same way as new runs.
- A run changed after baselining is reported by `/audit/verify` like any other tampered run; baselining never runs again for a run that already has an entry.

### RC-124 Model change-control gate
As the system owner, I want a model change to be accepted only when the benchmark passes, so quality cannot drop silently when the provider changes models.
- `python -m evals.check_thresholds` exits 0 only if SQL accuracy ≥ 95%, root-cause Hit@1 ≥ 85%, correct refusals = 100% and unsupported numbers ≤ 2%.
- A failing report exits 1 and names each failed criterion.

### RC-125 User identity on every question (planned, gap G1)
As a QA auditor, I want each question linked to the person who asked it, so answers meet ALCOA+ "Attributable".
- The app requires sign-in through the company identity provider before a question can be asked.
- Each run and its audit entry store the user id.
- A request without a signed-in user is refused with 401 and no run is stored.

### RC-126 Periodic audit-trail review (planned, gap G3)
As a QA manager, I want a monthly audit-trail review report, so the review required by our procedures has evidence.
- The report lists the verification result, the number of entries checked and any problems found in the period.
- The report is generated on the 1st of each month at 06:00 UTC and saved as a PDF.
- If verification finds a problem, the system owner receives an email within 15 minutes.
- If the report cannot be generated, the system owner receives an email with the error, and the missed month is generated on the next successful run.

## Spec review (SpecCheck, 2026-09-25)
First run on this PRD: 0 blocking gaps, 4 medium. Response:
| Gap | Decision |
|---|---|
| RC-122 had no failure behaviour | Accepted: added the "failed before any model call" criterion |
| RC-123 had no failure behaviour | Accepted: added what happens when a baselined run is changed later |
| RC-123 "runs are verified" named no actor | Accepted: rewritten so the system (`/audit/verify`) is the actor |
| RC-126 had no failure behaviour | Accepted: added report-failure handling |
Re-run after the changes: see `docs/product/speccheck_v1.2/spec_review_v1.2.md`.

## Release plan
v1.2 (this release): RC-121 to RC-124. v1.3: RC-125 and RC-126, after an identity-provider decision.
