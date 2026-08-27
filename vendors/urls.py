from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("vendors", views.VendorViewSet, basename="vendors")
router.register("branches", views.BranchViewSet, basename="branches")

urlpatterns = [path("", include(router.urls))]
