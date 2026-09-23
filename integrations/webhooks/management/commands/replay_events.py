from django.core.management.base import BaseCommand

from webhooks.models import WebhookEvent
from webhooks.processing import replay


class Command(BaseCommand):
    help = "Replay one event by id, or all dead-lettered events (after fixing the cause)."

    def add_arguments(self, parser):
        parser.add_argument("event_ids", nargs="*", type=int)
        parser.add_argument("--dead-letter", action="store_true", help="Replay every dead-lettered event")

    def handle(self, *args, event_ids, dead_letter, **options):
        if dead_letter:
            event_ids = list(WebhookEvent.objects.filter(status=WebhookEvent.Status.DEAD_LETTER).values_list("pk", flat=True))
        for event_id in event_ids:
            self.stdout.write(f"event {event_id}: {replay(event_id)}")
        self.stdout.write(f"Replayed {len(event_ids)} event(s).")
