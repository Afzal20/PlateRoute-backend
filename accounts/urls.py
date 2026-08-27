from django.urls import include, path, re_path
from dj_rest_auth.views import PasswordResetView, PasswordResetConfirmView
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutAllView.as_view(), name="logout_all"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("password-reset/", PasswordResetView.as_view(), name="password_reset"),
    re_path(r"password-reset/confirm/(?P<uid>[^/]+)/(?P<token>[^/]+)/$", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("google/", include("allauth.socialaccount.urls")),
    path("google/login/", views.GoogleLoginView.as_view(), name="google_login"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
]
