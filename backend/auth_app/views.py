from django.conf import settings
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import AuthenticationFailed, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .email import (
    consume_reset_token,
    mark_verified,
    send_password_reset_email,
    send_verification_email,
    verify_reset_token,
    verify_token,
)
from .serializers import PasswordChangeSerializer, RegisterSerializer, UserSerializer
from .throttles import LoginThrottle, PasswordResetThrottle, ResendVerificationThrottle

User = get_user_model()


# ── Login — clear errors + blocks unverified accounts ─────────────────────
class RithaTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Call parent — raises AuthenticationFailed on bad credentials (HTTP 401)
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            raise AuthenticationFailed(
                "No account found with these credentials, or the password is incorrect."
            ) from None

        user = self.user
        if not user.is_email_verified:
            # Return a structured 403 the frontend can detect
            raise Exception(f"email_not_verified::{user.email}::Please verify your email before logging in.")
        return data


class LoginView(TokenObtainPairView):
    serializer_class = RithaTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except Exception as exc:
            msg = str(exc)
            if msg.startswith("email_not_verified::"):
                _, email, human_msg = msg.split("::", 2)
                return Response(
                    {
                        "error": {
                            "code": "email_not_verified",
                            "message": human_msg,
                            "email": email,
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
            raise  # let DRF handle AuthenticationFailed → 401


# ── Register ──────────────────────────────────────────────────────────────
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            # Return clear, human-readable field errors
            errors = {}
            for field, msgs in serializer.errors.items():
                errors[field] = msgs[0] if isinstance(msgs, list) else str(msgs)
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "Please fix the errors below.",
                        "detail": errors,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()
        sent = send_verification_email(user)

        return Response(
            {
                "email": user.email,
                "message": (
                    "Account created. Please check your email to verify your address before logging in."
                    if sent
                    else "Account created but the verification email could not be sent. Use the resend endpoint."
                ),
                "verification_sent": sent,
            },
            status=status.HTTP_201_CREATED,
        )


# ── Social sign-in (Google) ───────────────────────────────────────────────
def _google_audiences():
    # Comma-separated so the web client id and native (Android/iOS) client ids
    # are all accepted as valid ID-token audiences.
    raw = getattr(settings, "GOOGLE_CLIENT_ID", "")
    return [a.strip() for a in raw.split(",") if a.strip()]


class GoogleSocialLoginView(APIView):
    """Sign in / sign up with a Google ID token.

    The client obtains an ID token from Google Identity Services and POSTs it as
    ``{"credential": "<jwt>"}`` (GSI's field name; ``id_token`` also accepted). We
    verify it against our Google client id, find-or-create the user (linking by
    the Google-verified email), and return our own ``{access, refresh}`` pair —
    bypassing the password + email-verification login path entirely.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(summary="Sign in with a Google ID token", responses={200: None})
    def post(self, request):
        token = request.data.get("credential") or request.data.get("id_token") or ""
        if not token:
            return Response(
                {"error": {"code": "missing_token", "message": "No Google credential provided."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        audiences = _google_audiences()
        if not audiences:
            return Response(
                {"error": {"code": "google_not_configured", "message": "Google sign-in is not configured."}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token as google_id_token

            # Verify signature + issuer + expiry; the audience is checked against
            # our allowlist below so web + native client IDs are all accepted.
            payload = google_id_token.verify_oauth2_token(token, google_requests.Request())
        except Exception:
            return Response(
                {
                    "error": {
                        "code": "invalid_token",
                        "message": "Could not verify your Google sign-in. Please try again.",
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if payload.get("aud") not in audiences:
            return Response(
                {
                    "error": {
                        "code": "invalid_token",
                        "message": "Could not verify your Google sign-in. Please try again.",
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Google sets email_verified on real accounts; refuse anything else.
        if not payload.get("email") or not payload.get("email_verified", False):
            return Response(
                {"error": {"code": "email_unverified", "message": "Your Google account email is not verified."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = payload["email"].lower()
        sub = payload.get("sub", "")

        # Link by verified email: reuse an existing account if one matches.
        user = User.objects.filter(email__iexact=email).first()
        created = user is None
        if created:
            user = User.objects.create_user(
                email=email,
                password=None,  # unusable password — social-only account
                first_name=payload.get("given_name", ""),
                last_name=payload.get("family_name", ""),
            )
            user.auth_provider = "google"

        # Google verified the email for us, so the account is trusted.
        if not user.google_sub:
            user.google_sub = sub
        user.is_email_verified = True
        user.save()

        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh), "created": created})


# ── Social sign-in (Apple) ────────────────────────────────────────────────
# Apple's public keys are served as a JWKS; PyJWKClient caches them internally,
# so keep one client for the process.
_apple_jwk_client = None


def _get_apple_jwk_client():
    global _apple_jwk_client
    if _apple_jwk_client is None:
        from jwt import PyJWKClient

        _apple_jwk_client = PyJWKClient("https://appleid.apple.com/auth/keys")
    return _apple_jwk_client


def _apple_audiences():
    # Comma-separated so web (Services ID) and, later, a native app (bundle ID)
    # can both be accepted as valid token audiences.
    raw = getattr(settings, "APPLE_CLIENT_ID", "")
    return [a.strip() for a in raw.split(",") if a.strip()]


def _verify_apple_token(token, audiences):
    """Verify an Apple ID token (RS256) against Apple's JWKS. Patch point in tests."""
    import jwt

    signing_key = _get_apple_jwk_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=audiences,
        issuer="https://appleid.apple.com",
    )


class AppleSocialLoginView(APIView):
    """Sign in / sign up with an Apple ID token.

    The client runs Sign in with Apple, then POSTs ``{"id_token": "<jwt>"}`` (plus
    optional ``first_name``/``last_name`` — Apple only returns the name on the
    *first* authorization, so the web client forwards it then). We verify the
    token against Apple's JWKS, find-or-create the user (matching by the
    Apple-verified email, or the stable Apple ``sub``), and return our own
    ``{access, refresh}`` — bypassing the password + email-verification path.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(summary="Sign in with an Apple ID token", responses={200: None})
    def post(self, request):
        token = request.data.get("id_token") or request.data.get("credential") or ""
        if not token:
            return Response(
                {"error": {"code": "missing_token", "message": "No Apple credential provided."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        audiences = _apple_audiences()
        if not audiences:
            return Response(
                {"error": {"code": "apple_not_configured", "message": "Apple sign-in is not configured."}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            payload = _verify_apple_token(token, audiences)
        except Exception:
            return Response(
                {
                    "error": {
                        "code": "invalid_token",
                        "message": "Could not verify your Apple sign-in. Please try again.",
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        sub = payload.get("sub", "")
        email = (payload.get("email") or "").lower()

        # Match by the Apple-verified email if present, else by the stable sub
        # (a returning user who chose "Hide My Email" still has a constant sub).
        user = None
        if email:
            user = User.objects.filter(email__iexact=email).first()
        if user is None and sub:
            user = User.objects.filter(apple_sub=sub).first()

        created = user is None
        if created:
            if not email:
                return Response(
                    {
                        "error": {
                            "code": "no_email",
                            "message": "Apple didn't share an email for this account. Sign up with email first.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user = User.objects.create_user(
                email=email,
                password=None,  # unusable password — social-only account
                first_name=request.data.get("first_name", ""),
                last_name=request.data.get("last_name", ""),
            )
            user.auth_provider = "apple"

        if not user.apple_sub:
            user.apple_sub = sub
        # Backfill a name Apple only provides on the first sign-in.
        if not user.first_name and request.data.get("first_name"):
            user.first_name = request.data["first_name"]
        if not user.last_name and request.data.get("last_name"):
            user.last_name = request.data["last_name"]
        user.is_email_verified = True
        user.save()

        refresh = RefreshToken.for_user(user)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh), "created": created})


# ── Verify email ──────────────────────────────────────────────────────────
class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = None

    def post(self, request):
        token = request.data.get("token", "").strip()
        email = request.data.get("email", "").strip().lower()

        if not token or not email:
            return Response(
                {"error": {"code": "missing_fields", "message": "`token` and `email` are required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Anti-enumeration: an unknown email is indistinguishable from a bad token.
            return Response(
                {"error": {"code": "invalid_token", "message": "This verification link is invalid or has expired."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_email_verified:
            return Response({"message": "Email already verified. You can log in."})

        ok, error_msg = verify_token(user, token)
        if not ok:
            return Response(
                {"error": {"code": "invalid_token", "message": error_msg}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mark_verified(user)
        return Response({"message": "Email verified successfully. You can now log in."})


# ── Resend verification ───────────────────────────────────────────────────
class ResendVerificationView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ResendVerificationThrottle]
    serializer_class = None

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response(
                {"error": {"code": "missing_fields", "message": "`email` is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            # Vague on purpose — don't reveal whether account exists
            return Response({"message": "If that email is registered and unverified, we sent a new link."})

        if user.is_email_verified:
            return Response({"message": "This email is already verified. You can log in."})

        send_verification_email(user)
        return Response({"message": "Verification email sent. Please check your inbox."})


# ── Forgot password — request reset ──────────────────────────────────────
class ForgotPasswordView(APIView):
    """POST /api/auth/forgot-password/  body: { email }"""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]
    serializer_class = None

    @extend_schema(
        summary="Request a password reset email",
        description=(
            "Sends a password-reset link to the given email address. "
            "Always returns 200 regardless of whether the email is registered "
            "(prevents user enumeration)."
        ),
        responses={200: None},
    )
    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return Response(
                {"error": {"code": "missing_fields", "message": "`email` is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        generic_ok = Response(
            {
                "message": (
                    "If an account exists for that email address, we have sent a password-reset link. Check your inbox."
                )
            }
        )

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            # Anti-enumeration: pretend success for unknown emails.
            return generic_ok

        sent = send_password_reset_email(user)
        if not sent:
            # Log server-side, but still return the SAME generic response — a distinguishing
            # 500 for real accounts would defeat the anti-enumeration guarantee above.
            import logging

            logging.getLogger(__name__).error("Password-reset email failed to send for user %s", user.pk)
        return generic_ok


def _revoke_refresh_tokens(user):
    """Blacklist all of a user's outstanding refresh tokens — forces re-auth on every
    device after a password reset/change, limiting post-compromise session persistence."""
    from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


# ── Reset password — consume token ────────────────────────────────────────
class ResetPasswordView(APIView):
    """POST /api/auth/reset-password/  body: { token, email, new_password }"""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]
    serializer_class = None

    @extend_schema(
        summary="Reset password using a token from email",
        description="Validates the reset token and sets a new password.",
        responses={200: None},
    )
    def post(self, request):
        token = request.data.get("token", "").strip()
        email = request.data.get("email", "").strip().lower()
        new_password = request.data.get("new_password", "").strip()

        if not all([token, email, new_password]):
            return Response(
                {"error": {"code": "missing_fields", "message": "`token`, `email`, and `new_password` are required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 8:
            return Response(
                {"error": {"code": "password_too_short", "message": "New password must be at least 8 characters."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from django.contrib.auth.password_validation import validate_password

            validate_password(new_password)
        except Exception as exc:
            return Response(
                {"error": {"code": "password_invalid", "message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            # Anti-enumeration: an unknown email is indistinguishable from a bad token.
            return Response(
                {"error": {"code": "invalid_token", "message": "This reset link is invalid or has expired."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ok, error_msg = verify_reset_token(user, token)
        if not ok:
            return Response(
                {"error": {"code": "invalid_token", "message": error_msg}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        consume_reset_token(user, new_password)
        _revoke_refresh_tokens(user)  # invalidate any existing sessions on password reset
        return Response({"message": "Password reset successfully. You can now log in."})


# ── Me ────────────────────────────────────────────────────────────────────
class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# ── Password change (authenticated) ──────────────────────────────────────
class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        _revoke_refresh_tokens(request.user)  # invalidate other sessions on password change
        return Response({"detail": "Password changed successfully."})


# ── Logout ────────────────────────────────────────────────────────────────
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "`refresh` token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


# ── Delete account ────────────────────────────────────────────────────────
class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None

    def delete(self, request):
        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Push token ────────────────────────────────────────────────────────────
class RegisterPushTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None

    def post(self, request):
        token = request.data.get("token", None)
        enabled = request.data.get("enabled", True)
        request.user.device_push_token = token or ""
        request.user.push_notifications = bool(enabled)
        request.user.save(update_fields=["device_push_token", "push_notifications"])
        return Response(
            {
                "status": "registered" if token else "unregistered",
                "enabled": request.user.push_notifications,
            }
        )
