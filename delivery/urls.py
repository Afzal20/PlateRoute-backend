from django.urls import path

from . import views

urlpatterns = [
    path("delivery/profile/", views.ProfileView.as_view(), name="courier-profile"),
    path("delivery/offers/", views.OfferListView.as_view(), name="courier-offers"),
    path("delivery/offers/<int:pk>/<slug:action>/", views.OfferActionView.as_view(), name="courier-offer-action"),
    path("delivery/tasks/<uuid:uuid>/trip/", views.TripView.as_view(), name="courier-trip"),
    path("delivery/pings/", views.PingView.as_view(), name="courier-pings"),
    path("delivery/orders/<uuid:order_uuid>/tracking/", views.TrackingView.as_view(), name="order-tracking"),
]
