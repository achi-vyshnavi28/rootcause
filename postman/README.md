# Postman API regression suite

`RootCause.postman_collection.json`: 13 requests, 30 assertions, generated from `build_collection.py` so every
request and assertion can be reviewed in one file.

| Area | What is checked |
|---|---|
| Input validation | Too-short question → 422; unknown dataset → 400 before any LLM call; feedback rating out of range → 422; unknown run → 404 |
| A known-answer question | "How many orders were canceled?" → status ok, answer contains the true count (625), cites its query, no unsupported numbers, every executed query was validated (has a LIMIT) |
| Stored record | The saved run matches what was returned and records the model that answered |
| Audit trail (21 CFR Part 11 §11.10(e)) | Query trail present; the audit log is hash-chained (SHA-256, each entry links to the previous); `/audit/verify` reports the trail intact |
| Model change control | The latest benchmark meets the acceptance thresholds in `docs/gxp/04_validation_approach_and_traceability.md` |

## Run
```bash
uvicorn backend.api.main:app --port 8700
cd postman
npx newman run RootCause.postman_collection.json -e local.postman_environment.json --timeout-request 600000
```
Or import both JSON files into Postman. Request 05 calls the LLM (needs `GEMINI_API_KEY`); the rest are instant.

Last run (2026-09-25, PostgreSQL, gemini-3.6-flash): **13/13 requests, 30/30 assertions passed** (`newman_last_run.json`).
