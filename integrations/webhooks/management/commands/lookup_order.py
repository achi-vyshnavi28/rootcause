from django.core.management.base import BaseCommand

from webhooks.models import OrderRecord, ReconciliationIssue, WebhookEvent


class Command(BaseCommand):
    help = "Show everything we know about an order: current state, webhook history, open issues."

    def add_arguments(self, parser):
        parser.add_argument("order_id")

    def handle(self, *args, order_id, **options):
        record = OrderRecord.objects.filter(order_id=order_id).first()
        self.stdout.write(f"Order {order_id}: " + (
            f"payment={record.payment_status or '-'} amount_paise={record.amount_paise} shipment={record.shipment_status or '-'}"
            if record else "NOT FOUND locally"))
        for e in WebhookEvent.objects.filter(order_id=order_id).order_by("occurred_at"):
            self.stdout.write(f"  [{e.status:<11}] {e.provider:<10} {e.event_type:<22} occurred={e.occurred_at} "
                              f"attempts={e.attempts} {e.last_error[:80]}")
        for i in ReconciliationIssue.objects.filter(order_id=order_id, resolved=False):
            self.stdout.write(self.style.WARNING(f"  OPEN ISSUE {i.kind}: local={i.local_value} provider={i.provider_value}"))
