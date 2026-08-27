from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("restaurants", views.RestaurantViewSet, basename="discovery-restaurants")

urlpatterns = [path("", include(router.urls))]
