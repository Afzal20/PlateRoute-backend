from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("addresses", views.AddressViewSet, basename="addresses")

urlpatterns = [path("geocode/", views.GeocodeView.as_view(), name="geocode"), path("", include(router.urls))]
