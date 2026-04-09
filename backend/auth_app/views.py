from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from drf_spectacular.utils import extend_schema
from django.contrib.auth import get_user_model

from .serializers import RegisterSerializer, UserSerializer, PasswordChangeSerializer
from .email import (
    send_verification_email, verify_token, mark_verified,
    send_password_reset_email, verify_reset_token, consume_reset_token,
)
from .throttles import ResendVerificationThrottle, LoginThrottle, PasswordResetThrottle

User = get_user_model()


# ── Login — clear errors + blocks unverified accounts ─────────────────────
class ArokahTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Call parent — raises AuthenticationFailed on bad credentials (HTTP 401)
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            raise AuthenticationFailed(
                'No account found with these credentials, or the password is incorrect.'
            )

        user = self.user
        if not user.is_email_verified:
            # Return a structured 403 the frontend can detect
            raise Exception(
                f'email_not_verified::{user.email}::Please verify your email before logging in.'
            )
        return data


class LoginView(TokenObtainPairView):
    serializer_class = ArokahTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except Exception as exc:
            msg = str(exc)
            if msg.startswith('email_not_verified::'):
                _, email, human_msg = msg.split('::', 2)
                return Response(
                    {'error': {
                        'code':    'email_not_verified',
                        'message': human_msg,
                        'email':   email,
                    }},
                    status=status.HTTP_403_FORBIDDEN,
                )
            raise  # let DRF handle AuthenticationFailed → 401


# ── Register ──────────────────────────────────────────────────────────────
class RegisterView(generics.CreateAPIView):
    queryset           = User.objects.all()
    serializer_class   = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        import logging
        logging.basicConfig(level=logging.INFO)
        logging.info(f"Register request data: {request.data}")
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            logging.error(f"Serializer errors: {serializer.errors}")
            # Return clear, human-readable field errors
            errors = {}
            for field, msgs in serializer.errors.items():
                errors[field] = msgs[0] if isinstance(msgs, list) else str(msgs)
            return Response(
                {'error': {
                    'code':    'validation_error',
                    'message': 'Please fix the errors below.',
                    'detail':  errors,
                }},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()
        sent = send_verification_email(user)

        return Response(
            {
                'email':             user.email,
                'message':           (
                    'Account created. Please check your email to verify your address before logging in.'
                    if sent else
                    'Account created but the verification email could not be sent. Use the resend endpoint.'
                ),
                'verification_sent': sent,
            },
            status=status.HTTP_201_CREATED,
        )


# ── Verify email ──────────────────────────────────────────────────────────
class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class   = None

    def post(self, request):
        token = request.data.get('token', '').strip()
        email = request.data.get('email', '').strip().lower()

        if not token or not email:
            return Response(
                {'error': {'code': 'missing_fields', 'message': '`token` and `email` are required.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {'error': {'code': 'not_found', 'message': 'No account found for this email.'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_email_verified:
            return Response({'message': 'Email already verified. You can log in.'})

        ok, error_msg = verify_token(user, token)
        if not ok:
            return Response(
                {'error': {'code': 'invalid_token', 'message': error_msg}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mark_verified(user)
        return Response({'message': 'Email verified successfully. You can now log in.'})


# ── Resend verification ───────────────────────────────────────────────────
class ResendVerificationView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes   = [ResendVerificationThrottle]
    serializer_class   = None

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response(
                {'error': {'code': 'missing_fields', 'message': '`email` is required.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            # Vague on purpose — don't reveal whether account exists
            return Response({'message': 'If that email is registered and unverified, we sent a new link.'})

        if user.is_email_verified:
            return Response({'message': 'This email is already verified. You can log in.'})

        send_verification_email(user)
        return Response({'message': 'Verification email sent. Please check your inbox.'})


# ── Forgot password — request reset ──────────────────────────────────────
class ForgotPasswordView(APIView):
    """POST /api/auth/forgot-password/  body: { email }"""
    permission_classes = [permissions.AllowAny]
    throttle_classes   = [PasswordResetThrottle]
    serializer_class   = None

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
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response(
                {'error': {'code': 'missing_fields', 'message': '`email` is required.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        generic_ok = Response({
            'message': (
                'If an account exists for that email address, '
                'we have sent a password-reset link. Check your inbox.'
            )
        })

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            # Anti-enumeration: pretend success for unknown emails.
            return generic_ok

        sent = send_password_reset_email(user)
        if not sent:
            # Real account, but SMTP failed — surface so user/ops can act.
            return Response(
                {'error': {
                    'code': 'email_send_failed',
                    'message': (
                        'We could not send the password reset email. '
                        'Check the server logs for the SMTP error (most often: '
                        'Gmail requires an App Password, not your account password).'
                    ),
                }},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return generic_ok


# ── Reset password — consume token ────────────────────────────────────────
class ResetPasswordView(APIView):
    """POST /api/auth/reset-password/  body: { token, email, new_password }"""
    permission_classes = [permissions.AllowAny]
    throttle_classes   = [PasswordResetThrottle]
    serializer_class   = None

    @extend_schema(
        summary="Reset password using a token from email",
        description="Validates the reset token and sets a new password.",
        responses={200: None},
    )
    def post(self, request):
        token        = request.data.get('token', '').strip()
        email        = request.data.get('email', '').strip().lower()
        new_password = request.data.get('new_password', '').strip()

        if not all([token, email, new_password]):
            return Response(
                {'error': {'code': 'missing_fields',
                           'message': '`token`, `email`, and `new_password` are required.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_password) < 8:
            return Response(
                {'error': {'code': 'password_too_short',
                           'message': 'New password must be at least 8 characters.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from django.contrib.auth.password_validation import validate_password
            validate_password(new_password)
        except Exception as exc:
            return Response(
                {'error': {'code': 'password_invalid', 'message': str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            return Response(
                {'error': {'code': 'not_found', 'message': 'No account found for this email.'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        ok, error_msg = verify_reset_token(user, token)
        if not ok:
            return Response(
                {'error': {'code': 'invalid_token', 'message': error_msg}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        consume_reset_token(user, new_password)
        return Response({'message': 'Password reset successfully. You can now log in.'})


# ── Me ────────────────────────────────────────────────────────────────────
class MeView(generics.RetrieveUpdateAPIView):
    serializer_class   = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


# ── Password change (authenticated) ──────────────────────────────────────
class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'detail': 'Password changed successfully.'})


# ── Logout ────────────────────────────────────────────────────────────────
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': '`refresh` token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


# ── Delete account ────────────────────────────────────────────────────────
class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    def delete(self, request):
        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Push token ────────────────────────────────────────────────────────────
class RegisterPushTokenView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    def post(self, request):
        token   = request.data.get('token', None)
        enabled = request.data.get('enabled', True)
        request.user.device_push_token  = token or ''
        request.user.push_notifications = bool(enabled)
        request.user.save(update_fields=['device_push_token', 'push_notifications'])
        return Response({
            'status':  'registered' if token else 'unregistered',
            'enabled': request.user.push_notifications,
        })
