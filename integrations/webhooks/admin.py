from django.contrib import admin

from .models import OrderRecord, ReconciliationIssue, WebhookEvent


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "event_type", "order_id", "status", "attempts", "received_at")
    list_filter = ("provider", "status")
    search_fields = ("order_id", "event_id")


admin.site.register(OrderRecord)
admin.site.register(ReconciliationIssue)
