import secrets

from django.conf import settings
from django.db import models

# Human-readable alphabet with ambiguous characters removed (no 0/O/1/I/L).
_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def normalize_code(code: str) -> str:
    """Codes are stored and compared upper-cased and stripped, so ``?ref=maya20``
    matches an admin-entered ``MAYA20``."""
    return (code or "").strip().upper()


def generate_referral_code(length: int = 8) -> str:
    """Collision-checked random code, mirroring ``ensure_invite_token`` in
    shared_wardrobe but human-shareable rather than opaque."""
    for _ in range(8):
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))
        if not ReferralCode.objects.filter(code=code).exists():
            return code
    # Effectively unreachable; widen the space rather than risk a collision.
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length + 4))


class ReferralCode(models.Model):
    """An influencer / campaign code handed out by the owner. Shared as
    ``/?ref=<code>`` and attributed to new signups via ``ReferralSignup``."""

    code = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        blank=True,
        help_text="Shareable code, e.g. MAYA20. Auto-generated if left blank.",
    )
    name = models.CharField(max_length=120, help_text="Influencer or campaign name.")
    note = models.TextField(blank=True, default="")
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive codes stop attributing new signups (existing ones are kept).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.code = normalize_code(self.code)
        if not self.code:
            self.code = generate_referral_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} ({self.name})"

    @property
    def signup_count(self) -> int:
        return self.signups.count()

    @property
    def verified_count(self) -> int:
        return self.signups.filter(user__is_email_verified=True).count()

    @property
    def share_path(self) -> str:
        return f"/?ref={self.code}"


class ReferralSignup(models.Model):
    """One attributed signup. OneToOne on user → a user is attributed to at most
    one code (first code wins), so ``code.signups.count()`` is the tracker."""

    code = models.ForeignKey(ReferralCode, on_delete=models.CASCADE, related_name="signups")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user_id} via {self.code.code}"
