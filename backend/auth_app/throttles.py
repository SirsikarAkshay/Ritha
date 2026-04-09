from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class ResendVerificationThrottle(AnonRateThrottle):
    """
    Max 3 resend-verification requests per email address per hour.
    Uses the request IP as cache key (anon users have no user id).
    """
    scope = 'resend_verification'


class LoginThrottle(AnonRateThrottle):
    """Max 10 login attempts per IP per 15 minutes — brute-force protection."""
    scope = 'login_attempts'


class PasswordResetThrottle(AnonRateThrottle):
    """Max 5 password-reset requests per IP per hour — prevent email flooding."""
    scope = 'password_reset'
