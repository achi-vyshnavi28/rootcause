from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import WebhookEvent
from .processing import handle_event, reconcile
from .providers import ProviderClient


@shared_task(acks_late=True)
def process_event(event_id: int) -> str:
    status = handle_event(event_id)
    if status == WebhookEvent.Status.FAILED and not settings.CELERY_TASK_ALWAYS_EAGER:
        attempts = WebhookEvent.objects.get(pk=event_id).attempts
        process_event.apply_async((event_id,), countdown=min(2 ** attempts * 10, 3600))  # exponential backoff
    return status


@shared_task
def retry_failed_events() -> int:
    """Safety net: re-queue failed events whose scheduled retry was lost (e.g. worker restart)."""
    stale = WebhookEvent.objects.filter(status=WebhookEvent.Status.FAILED,
                                        received_at__lt=timezone.now() - timedelta(minutes=10))
    ids = list(stale.values_list("pk", flat=True))
    for event_id in ids:
        process_event.delay(event_id)
    return len(ids)


@shared_task
def run_reconciliation() -> int:
    client = ProviderClient(settings.PROVIDER_API_BASE_URL, settings.PROVIDER_CLIENT_ID, settings.PROVIDER_CLIENT_SECRET)
    since = (timezone.now() - timedelta(days=2)).isoformat()
    return len(reconcile(client, since))
