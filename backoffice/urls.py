from django.urls import path

from . import views

urlpatterns = [
    path("backoffice/orders/", views.OrdersBoardView.as_view(), name="ops-orders"),
    path("backoffice/refunds/", views.RefundQueueView.as_view(), name="ops-refunds"),
    path("backoffice/config/", views.ConfigBridgeView.as_view(), name="ops-config"),
]