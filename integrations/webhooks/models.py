from django.db import models


class WebhookEvent(models.Model):
    """Every webhook we accept, stored before processing so nothing is lost and anything can be replayed."""

    class Status(models.TextChoices):
        RECEIVED = "received"
        PROCESSED = "processed"
        FAILED = "failed"  # will be retried
        DEAD_LETTER = "dead_letter"  # gave up; needs a human, then replay

    provider = models.CharField(max_length=32)
    event_id = models.CharField(max_length=128, help_text="Provider's id, or a hash of the body: the idempotency key")
    event_type = models.CharField(max_length=64)
    order_id = models.CharField(max_length=64, blank=True, db_index=True)
    occurred_at = models.DateTimeField(null=True, help_text="When the provider says it happened (for ordering)")
    payload = models.JSONField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RECEIVED, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["provider", "event_id"], name="unique_provider_event")]
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.provider}:{self.event_type}:{self.event_id} ({self.status})"


class OrderRecord(models.Model):
    """Our view of an order's payment and shipment state, built from webhooks."""

    order_id = models.CharField(max_length=64, unique=True)
    payment_status = models.CharField(max_length=32, blank=True)
    shipment_status = models.CharField(max_length=32, blank=True)
    amount_paise = models.BigIntegerField(null=True)
    payment_updated_at = models.DateTimeField(null=True)
    shipment_updated_at = models.DateTimeField(null=True)


class ReconciliationIssue(models.Model):
    """A difference between our records and the provider's, found by the nightly job."""

    class Kind(models.TextChoices):
        MISSING_LOCALLY = "missing_locally"  # provider has it, we never got (or lost) the webhook
        STATUS_MISMATCH = "status_mismatch"
        AMOUNT_MISMATCH = "amount_mismatch"

    found_at = models.DateTimeField(auto_now_add=True)
    order_id = models.CharField(max_length=64)
    kind = models.CharField(max_length=32, choices=Kind.choices)
    local_value = models.CharField(max_length=64, blank=True)
    provider_value = models.CharField(max_length=64, blank=True)
    resolved = models.BooleanField(default=False)
