"""
Email utilities: verification + password reset.
All emails include both plain-text and HTML versions.
"""
import secrets
import logging
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone as dj_timezone

logger = logging.getLogger('arokah.email')


# ── Shared helpers ─────────────────────────────────────────────────────────

def _send(*, to: str, subject: str, text: str, html: str) -> bool:
    try:
        send_mail(
            subject=subject,
            message=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to],
            html_message=html,
            fail_silently=False,
        )
        logger.info('Email "%s" sent to %s', subject, to)
        return True
    except Exception as exc:
        logger.error('Failed to send "%s" to %s: %s', subject, to, exc)
        return False


def _email_wrapper(*, title: str, preheader: str, body_html: str, cta_url: str = '', cta_label: str = '') -> str:
    """Shared HTML shell for all Arokah transactional emails."""
    cta_block = ''
    if cta_url and cta_label:
        cta_block = f"""
        <table cellpadding="0" cellspacing="0" style="margin:0 0 28px;">
          <tr><td style="background:#D4724A;border-radius:12px;">
            <a href="{cta_url}"
               style="display:inline-block;padding:14px 32px;font-size:15px;font-weight:500;color:#ffffff;text-decoration:none;">
              {cta_label}
            </a>
          </td></tr>
        </table>"""

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:#0A0A0B;font-family:'DM Sans',system-ui,sans-serif;color:#F0EAD9;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0A0A0B;padding:40px 20px;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;">
        <tr><td style="padding-bottom:32px;">
          <span style="font-family:Georgia,serif;font-size:24px;color:#F0EAD9;letter-spacing:-0.02em;">Arokah</span>
          <span style="display:block;font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:#D4724A;margin-top:4px;">AI Style Companion</span>
        </td></tr>
        <tr><td style="background:#111113;border:1px solid rgba(255,255,255,0.07);border-radius:20px;padding:40px;">
          <h1 style="margin:0 0 16px;font-family:Georgia,serif;font-size:26px;font-weight:400;color:#F0EAD9;line-height:1.2;">{title}</h1>
          {body_html}
          {cta_block}
          <hr style="border:none;border-top:1px solid rgba(255,255,255,0.07);margin:0 0 20px;">
          <p style="margin:0;font-size:12px;color:rgba(176,160,144,0.5);line-height:1.5;">{preheader}</p>
        </td></tr>
        <tr><td style="padding-top:24px;text-align:center;">
          <p style="margin:0;font-size:11px;color:rgba(176,160,144,0.3);">Arokah · Dress for your day. Every day. 🌍</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


# ── Email verification ─────────────────────────────────────────────────────

def generate_verification_token() -> str:
    return secrets.token_hex(24)  # 48 hex chars, 192 bits


def send_verification_email(user) -> bool:
    token = generate_verification_token()
    user.email_verification_token = token
    user.email_token_created_at   = dj_timezone.now()
    user.save(update_fields=['email_verification_token', 'email_token_created_at'])

    verify_url  = f"{settings.FRONTEND_URL}/verify-email?token={token}&email={user.email}"
    name        = user.first_name or 'there'

    body_html = f"""
    <p style="margin:0 0 24px;font-size:15px;color:#B8B0A0;line-height:1.6;">
      Hi {name}, welcome to Arokah.<br>
      Click below to confirm your email address and activate your account.
    </p>
    <p style="margin:0 0 8px;font-size:13px;color:#B8B0A0;">Or copy this link:</p>
    <p style="margin:0 0 24px;font-size:12px;color:#D4724A;word-break:break-all;">{verify_url}</p>
    <p style="margin:0 0 24px;font-size:13px;color:#B8B0A0;">This link expires in <strong style="color:#F0EAD9;">24 hours</strong>.</p>
    """

    text = f"""Hi {name},

Welcome to Arokah.

Verify your email: {verify_url}

This link expires in 24 hours.

If you didn't create a Arokah account, ignore this email.
"""

    return _send(
        to=user.email,
        subject="Verify your Arokah email address",
        text=text,
        html=_email_wrapper(
            title="Verify your email",
            preheader="If you didn't create a Arokah account, you can safely ignore this email.",
            body_html=body_html,
            cta_url=verify_url,
            cta_label="Verify email address",
        ),
    )


def verify_token(user, token: str) -> tuple[bool, str]:
    if not user.email_verification_token:
        return False, 'No verification token found. Please request a new one.'
    if user.email_verification_token != token:
        return False, 'Invalid verification token.'
    if not user.email_token_created_at:
        return False, 'Token has no creation timestamp. Please request a new one.'

    age     = (dj_timezone.now() - user.email_token_created_at).total_seconds()
    timeout = getattr(settings, 'EMAIL_VERIFICATION_TIMEOUT', 86400)
    if age > timeout:
        return False, 'Verification link has expired. Please request a new one.'
    return True, ''


def mark_verified(user) -> None:
    user.is_email_verified        = True
    user.email_verification_token = ''
    user.email_token_created_at   = None
    user.save(update_fields=['is_email_verified', 'email_verification_token', 'email_token_created_at'])
    logger.info('Email verified for %s', user.email)


# ── Password reset ─────────────────────────────────────────────────────────

def generate_password_reset_token() -> str:
    return secrets.token_hex(24)  # 48 hex chars


def send_password_reset_email(user) -> bool:
    token = generate_password_reset_token()
    user.password_reset_token      = token
    user.password_reset_created_at = dj_timezone.now()
    user.save(update_fields=['password_reset_token', 'password_reset_created_at'])

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}&email={user.email}"
    name      = user.first_name or 'there'

    body_html = f"""
    <p style="margin:0 0 16px;font-size:15px;color:#B8B0A0;line-height:1.6;">
      Hi {name},<br>
      We received a request to reset your Arokah password.
      Click below to choose a new one.
    </p>
    <p style="margin:0 0 8px;font-size:13px;color:#B8B0A0;">Or copy this link:</p>
    <p style="margin:0 0 24px;font-size:12px;color:#D4724A;word-break:break-all;">{reset_url}</p>
    <p style="margin:0 0 24px;font-size:13px;color:#B8B0A0;">
      This link expires in <strong style="color:#F0EAD9;">1 hour</strong>.<br>
      If you didn't request a password reset, you can safely ignore this email — your password won't change.
    </p>
    """

    text = f"""Hi {name},

Reset your Arokah password: {reset_url}

This link expires in 1 hour.

If you didn't request this, ignore this email — your password won't change.
"""

    return _send(
        to=user.email,
        subject="Reset your Arokah password",
        text=text,
        html=_email_wrapper(
            title="Reset your password",
            preheader="If you didn't request a password reset, ignore this email.",
            body_html=body_html,
            cta_url=reset_url,
            cta_label="Reset password",
        ),
    )


def verify_reset_token(user, token: str) -> tuple[bool, str]:
    if not getattr(user, 'password_reset_token', ''):
        return False, 'No reset token found. Please request a new password reset.'
    if user.password_reset_token != token:
        return False, 'Invalid or already-used reset token.'
    if not user.password_reset_created_at:
        return False, 'Token has no creation timestamp. Please request a new reset.'

    age = (dj_timezone.now() - user.password_reset_created_at).total_seconds()
    if age > 3600:  # 1 hour
        return False, 'This reset link has expired. Please request a new one.'
    return True, ''


def consume_reset_token(user, new_password: str) -> None:
    """Set the new password and clear the reset token."""
    user.set_password(new_password)
    user.password_reset_token      = ''
    user.password_reset_created_at = None
    user.save(update_fields=['password', 'password_reset_token', 'password_reset_created_at'])
    logger.info('Password reset for %s', user.email)
