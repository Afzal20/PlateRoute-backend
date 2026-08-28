from django.urls import path

from . import views

urlpatterns = [
    path("notifications/devices/", views.DeviceRegistryView.as_view(), name="device-registry"),
    path("notifications/preferences/", views.PreferenceView.as_view(), name="notification-preferences"),
]