import json
import logging

from django.conf import settings
from django.db import IntegrityError, transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import OrderRecord, ReconciliationIssue, WebhookEvent
from .processing import PermanentError, extract, replay
from .serializers import OrderRecordSerializer, ReconciliationIssueSerializer, WebhookEventSerializer
from .signatures import body_hash, verify_razorpay, verify_token
from .tasks import process_event

log = logging.getLogger("webhooks")


def _accept(provider: str, event_id: str, body: bytes) -> Response:
    """Store first, then process asynchronously. Duplicates are acknowledged but not reprocessed."""
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return Response({"error": "invalid JSON"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        event_type, order_id, occurred_at = extract(provider, payload)
    except (PermanentError, ValueError, TypeError) as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    try:
        with transaction.atomic():  # savepoint: a duplicate must not poison the surrounding transaction
            event = WebhookEvent.objects.create(provider=provider, event_id=event_id, event_type=event_type,
                                                order_id=order_id, occurred_at=occurred_at, payload=payload)
    except IntegrityError:  # same provider + event id already stored: idempotent acknowledgement
        log.info("Duplicate %s event %s ignored", provider, event_id)
        return Response({"duplicate": True}, status=status.HTTP_200_OK)
    process_event.delay(event.pk)
    return Response({"id": event.pk}, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
def razorpay_webhook(request):
    body = request.body
    if not verify_razorpay(body, request.headers.get("X-Razorpay-Signature"), settings.RAZORPAY_WEBHOOK_SECRET):
        log.warning("Rejected Razorpay webhook with invalid signature")
        return Response({"error": "invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)
    return _accept("razorpay", request.headers.get("X-Razorpay-Event-Id") or body_hash(body), body)


@api_view(["POST"])
def shiprocket_webhook(request):
    if not verify_token(request.headers.get("X-Api-Key"), settings.SHIPROCKET_WEBHOOK_TOKEN):
        return Response({"error": "invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
    return _accept("shiprocket", body_hash(request.body), request.body)


@api_view(["GET"])
def health(_request):
    counts = {s: WebhookEvent.objects.filter(status=s).count() for s in WebhookEvent.Status.values}
    return Response({"status": "ok", "events": counts})


class WebhookEventViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = WebhookEventSerializer

    def get_queryset(self):
        qs = WebhookEvent.objects.all()
        for field in ("status", "provider", "order_id"):
            if value := self.request.query_params.get(field):
                qs = qs.filter(**{field: value})
        return qs

    @action(detail=True, methods=["post"])
    def replay(self, request, pk=None):
        self.get_object()
        return Response({"status": replay(int(pk))})


class OrderRecordViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = OrderRecordSerializer
    queryset = OrderRecord.objects.all()
    lookup_field = "order_id"


class ReconciliationIssueViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ReconciliationIssueSerializer
    queryset = ReconciliationIssue.objects.filter(resolved=False).order_by("-found_at")
