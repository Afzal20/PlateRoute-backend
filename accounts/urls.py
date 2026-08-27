from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutAllView.as_view(), name="logout_all"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "password-reset-otp/",
        views.PasswordResetOTPRequestView.as_view(),
        name="password_reset_otp",
    ),
    path(
        "password-reset-otp/confirm/",
        views.PasswordResetOTPConfirmView.as_view(),
        name="password_reset_otp_confirm",
    ),
    path("google/", include("allauth.socialaccount.urls")),
    path("google/login/", views.GoogleLoginView.as_view(), name="google_login"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
]
