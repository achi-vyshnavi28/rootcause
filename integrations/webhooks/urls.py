from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("events", views.WebhookEventViewSet, basename="event")
router.register("orders", views.OrderRecordViewSet, basename="order")
router.register("reconciliation-issues", views.ReconciliationIssueViewSet, basename="issue")

urlpatterns = [
    path("webhooks/razorpay/", views.razorpay_webhook),
    path("webhooks/shiprocket/", views.shiprocket_webhook),
    path("health/", views.health),
    path("api/", include(router.urls)),
]
