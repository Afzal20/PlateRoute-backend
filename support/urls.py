from django.urls import path

from . import views

urlpatterns = [
    path("support/tickets/", views.TicketView.as_view(), name="ticket-list-create"),
    path("support/tickets/<uuid:uuid>/", views.TicketDetailView.as_view(), name="ticket-detail"),
]