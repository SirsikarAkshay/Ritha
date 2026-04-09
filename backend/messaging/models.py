"""
1:1 messaging models.

A Conversation is the container for all messages between exactly two users.
We look conversations up via `Conversation.between(user_a, user_b)` which
normalizes the pair to avoid duplicates.
"""
from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """1:1 conversation. Exactly two participants via user_a / user_b.
    We normalize so that user_a.id < user_b.id to make lookups deterministic
    and prevent duplicate conversations for the same pair."""
    user_a     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_a',
    )
    user_b     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_b',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Per-user "marked as read up to this timestamp" pointers
    user_a_read_at = models.DateTimeField(null=True, blank=True)
    user_b_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user_a', 'user_b'], name='unique_conversation_pair'),
        ]
        indexes = [
            models.Index(fields=['user_a', '-updated_at']),
            models.Index(fields=['user_b', '-updated_at']),
        ]
        ordering = ['-updated_at']

    def __str__(self):
        return f'Conversation({self.user_a_id}, {self.user_b_id})'

    @classmethod
    def between(cls, user_a, user_b):
        """Return the canonical Conversation for (user_a, user_b), or None."""
        if user_a.pk == user_b.pk:
            return None
        lo, hi = sorted([user_a, user_b], key=lambda u: u.pk)
        return cls.objects.filter(user_a=lo, user_b=hi).first()

    @classmethod
    def get_or_create_between(cls, user_a, user_b):
        """Create if missing. Caller MUST verify the two users are connected."""
        if user_a.pk == user_b.pk:
            raise ValueError('Cannot create a conversation with yourself.')
        lo, hi = sorted([user_a, user_b], key=lambda u: u.pk)
        conv, created = cls.objects.get_or_create(user_a=lo, user_b=hi)
        return conv, created

    def other_user(self, me):
        return self.user_b if self.user_a_id == me.pk else self.user_a

    def has_participant(self, user) -> bool:
        return user.pk in (self.user_a_id, self.user_b_id)

    def unread_count_for(self, user) -> int:
        if not self.has_participant(user):
            return 0
        read_at = self.user_a_read_at if user.pk == self.user_a_id else self.user_b_read_at
        qs = self.messages.exclude(sender=user)
        if read_at:
            qs = qs.filter(created_at__gt=read_at)
        return qs.count()


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='messages_sent',
    )
    body         = models.TextField(max_length=4000)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['conversation', '-created_at']),
        ]
        ordering = ['created_at']

    def __str__(self):
        return f'Message({self.sender_id}): {self.body[:40]}'
