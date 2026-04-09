"""
Auto-create a Profile whenever a new User is created.
Handles are auto-suggested from first_name or the email local part.
"""
import re
import secrets

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()

HANDLE_ALLOWED = re.compile(r'[^a-z0-9_]')
HANDLE_MIN = 3
HANDLE_MAX = 20  # Leave headroom below Profile.handle max_length (30) for suffixes


def _sanitize(raw: str) -> str:
    raw = (raw or '').lower()
    raw = HANDLE_ALLOWED.sub('', raw)
    return raw[:HANDLE_MAX]


def generate_unique_handle(user) -> str:
    """Produce a unique lowercase handle derived from first_name or email local part."""
    from .models import Profile  # Local import to avoid app-registry issues at import time

    base = _sanitize(user.first_name) or _sanitize(user.email.split('@', 1)[0])
    if len(base) < HANDLE_MIN:
        base = f'user{secrets.token_hex(3)}'  # 6 hex chars → unique enough

    handle = base
    suffix = 0
    while Profile.objects.filter(handle=handle).exists():
        suffix += 1
        handle = f'{base}{suffix}'
        if suffix > 100:
            # Extremely unlikely, but don't loop forever
            handle = f'{base}_{secrets.token_hex(3)}'
            break
    return handle


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    if not created:
        return

    from .models import Profile  # Local import

    if hasattr(instance, 'profile'):
        return  # Defensive: already has one

    Profile.objects.create(
        user=instance,
        handle=generate_unique_handle(instance),
        display_name=instance.first_name or '',
    )
