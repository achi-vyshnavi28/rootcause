"""The 10+ failure scenarios from docs/runbooks/webhooks.md, each reproduced as a regression test."""

import json

import httpx
import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from webhooks import processing
from webhooks.models import OrderRecord, ReconciliationIssue, WebhookEvent
from webhooks.pii import mask
from webhooks.providers import ProviderClient, ProviderError
from webhooks.signatures import razorpay_signature

SECRET = "test-webhook-secret"


def razorpay_body(event="payment.captured", order_id="order_1", amount=49900, created_at=1_700_000_000) -> bytes:
    return json.dumps({"entity": "event", "event": event, "created_at": created_at,
                       "payload": {"payment": {"entity": {"id": "pay_1", "order_id": order_id,
                                                          "amount": amount, "status": event.split(".")[-1]}}}}).encode()


def post_razorpay(client, body: bytes, event_id="evt_1", signature=None):
    return client.post("/webhooks/razorpay/", data=body, content_type="application/json",
                       HTTP_X_RAZORPAY_SIGNATURE=signature or razorpay_signature(body, SECRET),
                       HTTP_X_RAZORPAY_EVENT_ID=event_id)


@pytest.fixture
def api():
    return APIClient()


@pytest.mark.django_db
def test_01_valid_webhook_is_stored_and_processed(api):
    r = post_razorpay(api, razorpay_body())
    assert r.status_code == 202
    order = OrderRecord.objects.get(order_id="order_1")
    assert (order.payment_status, order.amount_paise) == ("captured", 49900)
    assert WebhookEvent.objects.get().status == "processed"


@pytest.mark.django_db
def test_02_invalid_signature_is_rejected_and_not_stored(api):
    r = post_razorpay(api, razorpay_body(), signature="forged")
    assert r.status_code == 401
    assert WebhookEvent.objects.count() == 0


@pytest.mark.django_db
def test_03_duplicate_delivery_is_processed_once(api):
    body = razorpay_body()
    assert post_razorpay(api, body).status_code == 202
    r = post_razorpay(api, body)
    assert r.status_code == 200 and r.json()["duplicate"] is True
    assert WebhookEvent.objects.count() == 1


@pytest.mark.django_db
def test_04_out_of_order_events_do_not_overwrite_newer_state(api):
    post_razorpay(api, razorpay_body("payment.captured", created_at=2000), event_id="evt_new")
    post_razorpay(api, razorpay_body("payment.authorized", created_at=1000), event_id="evt_old")
    assert OrderRecord.objects.get(order_id="order_1").payment_status == "captured"


@pytest.mark.django_db
def test_05_malformed_json_returns_400(api):
    body = b"{not json"
    assert post_razorpay(api, body).status_code == 400


@pytest.mark.django_db
def test_06_event_without_order_id_goes_to_dead_letter_without_retries(api):
    post_razorpay(api, razorpay_body(order_id=""))
    event = WebhookEvent.objects.get()
    assert event.status == "dead_letter" and event.attempts == 1


@pytest.mark.django_db
def test_07_transient_failure_is_retried_then_succeeds(api, monkeypatch):
    real_apply, calls = processing.apply_event, {"n": 0}

    def flaky(event):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("database connection reset")
        real_apply(event)

    monkeypatch.setattr(processing, "apply_event", flaky)
    post_razorpay(api, razorpay_body())
    event = WebhookEvent.objects.get()
    assert event.status == "failed" and "connection reset" in event.last_error
    assert processing.handle_event(event.pk) == "processed"  # what the retry task does


@pytest.mark.django_db
@override_settings(MAX_EVENT_ATTEMPTS=3)
def test_08_repeated_failure_dead_letters_then_replay_after_fix(api, monkeypatch):
    real_apply = processing.apply_event
    monkeypatch.setattr(processing, "apply_event", lambda e: (_ for _ in ()).throw(RuntimeError("bug in handler")))
    post_razorpay(api, razorpay_body())
    event = WebhookEvent.objects.get()
    for _ in range(2):
        processing.handle_event(event.pk)
    event.refresh_from_db()
    assert event.status == "dead_letter" and event.attempts == 3

    monkeypatch.setattr(processing, "apply_event", real_apply)  # the bug is fixed and deployed
    r = api.post(f"/api/events/{event.pk}/replay/")
    assert r.json()["status"] == "processed"
    assert OrderRecord.objects.get(order_id="order_1").payment_status == "captured"


def _provider(handler) -> ProviderClient:
    return ProviderClient("https://provider.test", "id", "secret", transport=httpx.MockTransport(handler), sleep=lambda s: None)


def test_09_rate_limit_is_retried_honouring_retry_after():
    waits, calls = [], {"orders": 0}

    def handler(request):
        if request.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": "t1"})
        calls["orders"] += 1
        if calls["orders"] == 1:
            return httpx.Response(429, headers={"Retry-After": "3"})
        return httpx.Response(200, json={"items": [], "has_more": False})

    client = _provider(handler)
    client.sleep = waits.append
    assert client.list_orders("2018-01-01") == []
    assert waits == [3.0]


def test_10_expired_token_is_refreshed_once():
    tokens = iter(["expired", "fresh"])

    def handler(request):
        if request.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": next(tokens)})
        if request.headers["Authorization"] == "Bearer expired":
            return httpx.Response(401)
        return httpx.Response(200, json={"items": [{"order_id": "o1", "payment_status": "captured", "amount_paise": 100}], "has_more": False})

    assert _provider(handler).list_orders("2018-01-01")[0].order_id == "o1"


def test_11_persistent_server_error_raises_after_max_retries():
    def handler(request):
        if request.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": "t"})
        return httpx.Response(503)

    with pytest.raises(ProviderError):
        _provider(handler).list_orders("2018-01-01")


@pytest.mark.django_db
def test_12_reconciliation_finds_missing_and_mismatched_orders():
    OrderRecord.objects.create(order_id="o_ok", payment_status="captured", amount_paise=100)
    OrderRecord.objects.create(order_id="o_status", payment_status="authorized", amount_paise=100)
    OrderRecord.objects.create(order_id="o_amount", payment_status="captured", amount_paise=100)
    remote = [{"order_id": "o_ok", "payment_status": "captured", "amount_paise": 100},
              {"order_id": "o_status", "payment_status": "captured", "amount_paise": 100},
              {"order_id": "o_amount", "payment_status": "captured", "amount_paise": 150},
              {"order_id": "o_missing", "payment_status": "captured", "amount_paise": 200}]

    def handler(request):
        if request.url.path == "/oauth/token":
            return httpx.Response(200, json={"access_token": "t"})
        page = int(request.url.params["page"])
        return httpx.Response(200, json={"items": remote[(page - 1) * 2: page * 2], "has_more": page < 2})

    issues = processing.reconcile(_provider(handler), "2018-01-01")
    assert {(i.order_id, i.kind) for i in issues} == {
        ("o_status", "status_mismatch"), ("o_amount", "amount_mismatch"), ("o_missing", "missing_locally")}
    assert ReconciliationIssue.objects.count() == 3


@pytest.mark.django_db
def test_13_shiprocket_requires_token_and_updates_shipment(api):
    body = json.dumps({"order_id": "order_9", "awb": "123", "current_status": "DELIVERED",
                       "current_timestamp": "2018-06-10T10:00:00+00:00"})
    assert api.post("/webhooks/shiprocket/", data=body, content_type="application/json").status_code == 401
    r = api.post("/webhooks/shiprocket/", data=body, content_type="application/json", HTTP_X_API_KEY="test-shiprocket-token")
    assert r.status_code == 202
    assert OrderRecord.objects.get(order_id="order_9").shipment_status == "delivered"


def test_14_pii_is_masked_in_logs():
    text = mask("Customer ana.silva@example.com called from +55 11 98765-4321 about order_1")
    assert "ana.silva" not in text and "98765" not in text and "order_1" in text
