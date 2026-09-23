from rest_framework import serializers

from .models import OrderRecord, ReconciliationIssue, WebhookEvent


class WebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEvent
        fields = ["id", "provider", "event_id", "event_type", "order_id", "occurred_at", "status",
                  "attempts", "last_error", "received_at", "processed_at"]


class OrderRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderRecord
        fields = "__all__"


class ReconciliationIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReconciliationIssue
        fields = "__all__"
