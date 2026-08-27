from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("carts", views.CartViewSet, basename="carts")
router.register("carts/items", views.CartItemViewSet, basename="cart-items")

urlpatterns = [path("", include(router.urls))]
