from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    DeleteAccountView,
    ForgotPasswordView,
    GoogleSocialLoginView,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    RegisterPushTokenView,
    RegisterView,
    ResendVerificationView,
    ResetPasswordView,
    VerifyEmailView,
)

urlpatterns = [
    # Auth
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("social/google/", GoogleSocialLoginView.as_view(), name="social-google"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # Email verification
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),
    # Password reset (unauthenticated)
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    # Profile
    path("me/", MeView.as_view(), name="me"),
    path("me/password/", PasswordChangeView.as_view(), name="password-change"),
    path("me/delete/", DeleteAccountView.as_view(), name="delete-account"),
    # Push notifications
    path("push-token/", RegisterPushTokenView.as_view(), name="push-token"),
]
