from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("accounts.urls")),
    path("api/", include("common.urls")),
    path("api/v1/", include("addresses.urls")),
    path("api/v1/", include("vendors.urls")),
    path("api/v1/", include("menus.urls")),
    path("api/v1/", include("discovery.urls")),
    path("api/v1/", include("promotions.urls")),
    path("api/v1/", include("carts.urls")),
    path("api/v1/", include("orders.urls")),
    path("api/v1/", include("payments.urls")),
    path("api/v1/", include("delivery.urls")),
    path("api/v1/", include("chat.urls")),
    path("api/v1/", include("calls.urls")),
    path("api/v1/", include("notifications.urls")),
    path("api/v1/", include("reviews.urls")),
    path("api/v1/", include("support.urls")),
    path("api/v1/", include("analytics.urls")),
    path("api/v1/", include("backoffice.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema")),
]
