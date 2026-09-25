# Release notes: RootCause 1.2 (2026-09-25)

**Theme:** answers a regulated team can audit. Scope and reasoning: `docs/product/PRD_v1.2_gxp_readiness.md`
and the GxP assessment in `docs/gxp/`.

## What's new
- **Tamper-evident answer log.** Every saved answer is recorded in a hash chain with its SQL and the model that
  produced it. If anyone edits an answer or its SQL in the database, deletes a run, or inserts one outside the app,
  verification reports it.
- **"Audit trail intact" check in the History tab** (green when verified, red with the list of problems when not),
  and two API endpoints: `GET /audit/log` and `GET /audit/verify`.
- **Model recorded on every answer**, so a change in behaviour can be traced to a model change.
- **Model change-control gate:** `python -m evals.check_thresholds` accepts a new model only if the benchmark meets
  the acceptance criteria (exit code 1 = reject).
- **Existing answers protected from today:** the 64 answers saved before this release were baselined once at upgrade.

## Fixed
- BUG-001: the "Not helpful" feedback button label was cut off on wide screens.
- BUG-002: on the Windows development machine every question failed after a security-policy update blocked newer
  versions of three libraries; they are pinned to versions that load (see `docs/quality/bug_reports.md`).

## Quality evidence for this release
| Check | Result |
|---|---|
| Automated tests (`pytest`) | 96 passed (incl. 8 new audit-log and gate tests) |
| Browser tests (Playwright) | 4 of 4 passed; screenshots in `docs/quality/ui_evidence/` |
| API regression (Postman/Newman) | 13 of 13 requests, 30 of 30 assertions passed |
| Benchmark (unchanged agent) | SQL 100%, root-cause Hit@1 93.3%, refusals 100%, unsupported numbers 0% |
| Audit trail on the production database | Intact after baselining |

## Known limitations
- Questions are not yet linked to a signed-in user (planned v1.3, RC-125).
- The hash chain makes tampering visible, not impossible; database permissions that forbid changes to `audit_log`
  are a deployment task (gap G2 in `docs/gxp/02_risk_assessment.md`).

## Upgrade
No manual steps. The `audit_log` table is created and existing runs are baselined on first start.
