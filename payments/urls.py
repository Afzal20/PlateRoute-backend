from django.urls import path

from . import views

urlpatterns = [
    path("payments/<uuid:order_uuid>/start/", views.PaymentStartView.as_view(), name="payment-start"),
    path("payments/<uuid:order_uuid>/", views.PaymentStatusView.as_view(), name="payment-status"),
    path("payments/webhooks/<slug:provider>/", views.WebhookView.as_view(), name="payment-webhook"),
    path("payments/refunds/", views.RefundRequestView.as_view(), name="refund-request"),
    path("payments/refunds/<int:pk>/approve/", views.RefundApproveView.as_view(), name="refund-approve"),
]
