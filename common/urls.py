from django.urls import path

from . import views

urlpatterns = [
    path("healthz/", views.HealthView.as_view(), name="healthz"),
    path("v1/config/", views.ConfigView.as_view(), name="config"),
]
