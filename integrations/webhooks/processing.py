"""Turning stored webhook events into order state, safely and idempotently."""

import logging
from datetime import datetime, timezone

from django.conf import settings
from django.db import transaction
from django.utils import timezone as djtz

from .models import OrderRecord, ReconciliationIssue, WebhookEvent
from .providers import ProviderClient

log = logging.getLogger("webhooks")

RAZORPAY_STATUS = {"payment.authorized": "authorized", "payment.captured": "captured",
                   "payment.failed": "failed", "refund.processed": "refunded"}


class PermanentError(Exception):
    """Retrying will never fix this (bad payload). Goes straight to the dead-letter queue."""


def extract(provider: str, payload: dict) -> tuple[str, str, datetime | None]:
    """Return (event_type, order_id, occurred_at) from a provider payload."""
    if provider == "razorpay":
        entity = (payload.get("payload") or {}).get("payment", {}).get("entity", {})
        ts = payload.get("created_at")
        return payload.get("event", ""), entity.get("order_id") or "", datetime.fromtimestamp(ts, timezone.utc) if ts else None
    if provider == "shiprocket":
        ts = payload.get("current_timestamp")
        return "shipment." + str(payload.get("current_status", "")).lower(), str(payload.get("order_id") or ""), \
            datetime.fromisoformat(ts) if ts else None
    raise PermanentError(f"Unknown provider {provider}")


def apply_event(event: WebhookEvent) -> None:
    if not event.order_id:
        raise PermanentError("Event has no order id")
    with transaction.atomic():
        record, _ = OrderRecord.objects.select_for_update().get_or_create(order_id=event.order_id)
        if event.provider == "razorpay":
            status = RAZORPAY_STATUS.get(event.event_type)
            if status is None:
                return  # event type we don't track: acknowledge and ignore
            # Out-of-order delivery: never let an older event overwrite newer state.
            if record.payment_updated_at and event.occurred_at and event.occurred_at <= record.payment_updated_at:
                log.info("Skipping stale %s for %s", event.event_type, event.order_id)
                return
            entity = event.payload["payload"]["payment"]["entity"]
            record.payment_status, record.amount_paise = status, entity.get("amount")
            record.payment_updated_at = event.occurred_at
        else:
            if record.shipment_updated_at and event.occurred_at and event.occurred_at <= record.shipment_updated_at:
                return
            record.shipment_status = event.event_type.removeprefix("shipment.")
            record.shipment_updated_at = event.occurred_at
        record.save()


def handle_event(event_id: int) -> str:
    """Process one event. Returns the new status. Safe to call repeatedly (idempotent)."""
    event = WebhookEvent.objects.get(pk=event_id)
    if event.status == WebhookEvent.Status.PROCESSED:
        return event.status
    event.attempts += 1
    try:
        apply_event(event)
    except PermanentError as e:
        event.status, event.last_error = WebhookEvent.Status.DEAD_LETTER, str(e)
    except Exception as e:  # transient: DB hiccup, bug fixed later...
        event.last_error = f"{type(e).__name__}: {e}"
        event.status = (WebhookEvent.Status.DEAD_LETTER if event.attempts >= settings.MAX_EVENT_ATTEMPTS
                        else WebhookEvent.Status.FAILED)
        log.warning("Event %s failed (attempt %s): %s", event.pk, event.attempts, event.last_error)
    else:
        event.status, event.processed_at, event.last_error = WebhookEvent.Status.PROCESSED, djtz.now(), ""
    event.save()
    return event.status


def replay(event_id: int) -> str:
    """Give a failed / dead-lettered event a fresh start (after the underlying problem is fixed)."""
    WebhookEvent.objects.filter(pk=event_id).exclude(status=WebhookEvent.Status.PROCESSED).update(
        status=WebhookEvent.Status.RECEIVED, attempts=0, last_error="")
    return handle_event(event_id)


def reconcile(client: ProviderClient, since: str) -> list[ReconciliationIssue]:
    """Compare the provider's orders with ours and record every difference."""
    issues = []
    local = {r.order_id: r for r in OrderRecord.objects.all()}
    for remote in client.list_orders(since):
        mine = local.get(remote.order_id)
        if mine is None:
            issues.append(ReconciliationIssue(order_id=remote.order_id, kind=ReconciliationIssue.Kind.MISSING_LOCALLY,
                                              provider_value=remote.payment_status))
        elif mine.payment_status != remote.payment_status:
            issues.append(ReconciliationIssue(order_id=remote.order_id, kind=ReconciliationIssue.Kind.STATUS_MISMATCH,
                                              local_value=mine.payment_status, provider_value=remote.payment_status))
        elif mine.amount_paise is not None and mine.amount_paise != remote.amount_paise:
            issues.append(ReconciliationIssue(order_id=remote.order_id, kind=ReconciliationIssue.Kind.AMOUNT_MISMATCH,
                                              local_value=str(mine.amount_paise), provider_value=str(remote.amount_paise)))
    ReconciliationIssue.objects.bulk_create(issues)
    return issues
