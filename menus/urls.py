from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("menu/categories", views.CategoryViewSet, basename="menu-categories")
router.register("menu/items", views.ItemViewSet, basename="menu-items")

urlpatterns = [path("", include(router.urls))]
