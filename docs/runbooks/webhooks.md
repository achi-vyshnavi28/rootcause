# Runbook: payment & shipping webhooks

Service: `integrations/` (Django + DRF + Celery). Each scenario below has a regression test in
`integrations/integration_tests/test_webhooks.py` (test number in brackets).

## Quick tools
```bash
cd integrations
python manage.py lookup_order <order_id>          # state + full webhook history + open reconciliation issues
python manage.py replay_events <event_id> ...     # replay specific events
python manage.py replay_events --dead-letter      # replay everything in the dead-letter queue (after fixing the cause)
```
API: `GET /health/` (event counts by status) · `GET /api/events/?status=dead_letter` · `POST /api/events/<id>/replay/` · `GET /api/reconciliation-issues/`

## Scenarios

| # | Symptom | Likely cause | Check | Fix |
|---|---|---|---|---|
| 1 | Order paid but shows unpaid | Webhook not processed yet | `lookup_order`: is the event `received`/`failed`? | Wait for retry or replay the event |
| 2 | Provider dashboard shows webhook failures with 401 [02] | Wrong or rotated webhook secret | Compare `RAZORPAY_WEBHOOK_SECRET` with the provider dashboard | Update the secret; provider retries automatically |
| 3 | Same payment appears twice [03] | Provider retried delivery | Duplicates return 200 `{"duplicate": true}`; unique (provider, event_id) | None needed: idempotent by design |
| 4 | Status went backwards (captured → authorized) [04] | Events delivered out of order | `lookup_order` shows occurred_at order | None: older events are ignored by design |
| 5 | 400 responses in provider dashboard [05] | Provider sent malformed body | Server logs | Contact provider with the event id |
| 6 | Event in dead-letter with "no order id" [06] | Payload missing required field | `GET /api/events/?status=dead_letter` | Permanent: fix data manually or ask provider to resend |
| 7 | Events stuck in `failed` [07] | Transient DB/network error | `last_error` on the event | Retries run with backoff; `retry_failed_events` sweeps every 15 min |
| 8 | Growing dead-letter queue after deploy [08] | Bug in handler | `last_error` shows same exception | Fix and deploy, then `replay_events --dead-letter` |
| 9 | Reconciliation job slow / 429 in logs [09] | Provider rate limit | Log lines "retrying in Xs" | Automatic: client honours `Retry-After` |
| 10 | Reconciliation fails with 401 [10] | Expired OAuth token | Log "token expired; refreshing" | Automatic single refresh; if it keeps failing, rotate client credentials |
| 11 | Reconciliation errors with HTTP 503 [11] | Provider outage | Provider status page | Job fails loudly; rerun later |
| 12 | Open `missing_locally` / `status_mismatch` issues [12] | Lost webhooks, or events we don't handle | `GET /api/reconciliation-issues/` | Replay the provider's events, or correct state and mark the issue resolved |
| 13 | Shipment status never updates [13] | Shiprocket token mismatch (401) | `SHIPROCKET_WEBHOOK_TOKEN` vs dashboard | Update the token |

## Escalation template
```
Impact: <n orders / ₹ amount / merchants affected>, since <time>
Evidence: <event ids, lookup_order output, SQL counts>
Suspected cause: <...>
Actions taken: <replayed N events, rotated secret...>
Needs: <who / what decision>
```

## Data handling
Logs pass through `PiiMaskingFilter` (emails and phone numbers masked). Never paste raw payloads with customer data into tickets; use event ids.
