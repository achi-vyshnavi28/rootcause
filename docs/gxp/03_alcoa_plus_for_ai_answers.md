# 03 ALCOA+ for AI answers

ALCOA+ was written for records people create. For an AI analyst, each principle needs a concrete answer to
"how would an auditor check this?". Status: ✅ met · ⚠️ partly met · ❌ open.

| Principle | What it means for an AI answer | How RootCause meets it | Status |
|---|---|---|---|
| **Attributable** | Who asked, and which model answered | Model id per run (`usage.models`), stored in the audit entry. No user identity yet (gap G1) | ⚠️ |
| **Legible** | Readable by a person, now and later | Plain-English answer; every number cites a query id; SQL stored as executed | ✅ |
| **Contemporaneous** | Recorded when it happened | Run saved at completion with a UTC timestamp; the audit entry is written in the same database transaction | ✅ |
| **Original** | The first record is kept | Runs are never updated by the app; the audit log detects any later edit | ✅ |
| **Accurate** | The numbers are right | Grounding check (no number without evidence); 50-question benchmark: 100% SQL accuracy, 0% unsupported numbers | ✅ |
| **Complete** | Nothing missing, including failures | Failed SQL attempts are kept in the run (not only the successful one); errors are stored as runs with status `error` | ✅ |
| **Consistent** | Same order and format every time | One schema for every run; audit entries are strictly sequential and hash-linked | ✅ |
| **Enduring** | Survives for the retention period | Stored in PostgreSQL; backup and retention policy not defined (demo) | ⚠️ |
| **Available** | Can be retrieved for review or inspection | `GET /runs/{id}`, `/runs/{id}/audit`, `/audit/log`, `/audit/verify`; History tab in the UI | ✅ |

## The one thing ALCOA+ doesn't cover for AI
**Reproducibility.** The same question can give a different wording tomorrow, even with the same model. RootCause
handles this by making the *evidence* reproducible rather than the text: the stored SQL can be re-run against the same
data and must return the same numbers. That is what an investigator should rely on, and why every number cites a query.
