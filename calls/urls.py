from django.urls import path

from . import views

urlpatterns = [
    path("calls/", views.CallView.as_view(), name="call-start"),
    path("calls/<int:pk>/", views.CallView.as_view(), name="call-update"),
    path("calls/turn-credentials/", views.TurnCredentialsView.as_view(), name="call-turn-credentials"),
]