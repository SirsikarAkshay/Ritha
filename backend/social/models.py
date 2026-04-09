"""
Social graph models: Profile, Connection, BlockedUser.

Design notes:
- Handles are stored lowercase, uniqueness is case-insensitive by convention
  (we always normalize on write and query with handle__iexact where relevant).
- A Connection is a single directed row: sender (from_user) → recipient (to_user).
  Once `status='accepted'`, the relationship is considered symmetric; we do NOT
  insert a mirror row. Use `Connection.are_connected(a, b)` to check symmetrically.
- BlockedUser is one-way: blocker → blocked. If A blocks B, neither can send
  connection requests to the other or see the other in search.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


# ── Profile ────────────────────────────────────────────────────────────────

class ProfileVisibility(models.TextChoices):
    PUBLIC           = 'public',           'Public'
    CONNECTIONS_ONLY = 'connections_only', 'Connections only'


class Profile(models.Model):
    user              = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    handle            = models.CharField(max_length=30, unique=True, db_index=True)
    display_name      = models.CharField(max_length=80, blank=True)
    bio               = models.CharField(max_length=280, blank=True)
    avatar_url        = models.URLField(blank=True)
    visibility        = models.CharField(
        max_length=20,
        choices=ProfileVisibility.choices,
        default=ProfileVisibility.PUBLIC,
    )
    handle_changed_at = models.DateTimeField(null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['handle'])]

    def __str__(self):
        return f'@{self.handle}'

    def save(self, *args, **kwargs):
        if self.handle:
            self.handle = self.handle.lower()
        super().save(*args, **kwargs)


# ── Connection ─────────────────────────────────────────────────────────────

class ConnectionStatus(models.TextChoices):
    PENDING  = 'pending',  'Pending'
    ACCEPTED = 'accepted', 'Accepted'
    REJECTED = 'rejected', 'Rejected'


class Connection(models.Model):
    from_user  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='connections_sent',
    )
    to_user    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='connections_received',
    )
    status     = models.CharField(
        max_length=20,
        choices=ConnectionStatus.choices,
        default=ConnectionStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['from_user', 'to_user'],
                name='unique_connection_pair',
            ),
        ]
        indexes = [
            models.Index(fields=['to_user', 'status']),
            models.Index(fields=['from_user', 'status']),
        ]

    def __str__(self):
        return f'{self.from_user_id} → {self.to_user_id} ({self.status})'

    def clean(self):
        if self.from_user_id == self.to_user_id:
            raise ValidationError('Cannot connect to yourself.')

    @classmethod
    def between(cls, user_a, user_b):
        """Return the single Connection row between two users (either direction) or None."""
        return cls.objects.filter(
            models.Q(from_user=user_a, to_user=user_b)
            | models.Q(from_user=user_b, to_user=user_a)
        ).first()

    @classmethod
    def are_connected(cls, user_a, user_b) -> bool:
        """True iff an accepted connection exists in either direction."""
        if user_a.pk == user_b.pk:
            return False
        return cls.objects.filter(
            status=ConnectionStatus.ACCEPTED,
        ).filter(
            models.Q(from_user=user_a, to_user=user_b)
            | models.Q(from_user=user_b, to_user=user_a)
        ).exists()


# ── BlockedUser ────────────────────────────────────────────────────────────

class BlockedUser(models.Model):
    blocker    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blocks_made',
    )
    blocked    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blocks_received',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['blocker', 'blocked'],
                name='unique_block_pair',
            ),
        ]

    def __str__(self):
        return f'{self.blocker_id} blocks {self.blocked_id}'

    def clean(self):
        if self.blocker_id == self.blocked_id:
            raise ValidationError('Cannot block yourself.')

    @classmethod
    def is_blocked_either_way(cls, user_a, user_b) -> bool:
        return cls.objects.filter(
            models.Q(blocker=user_a, blocked=user_b)
            | models.Q(blocker=user_b, blocked=user_a)
        ).exists()
