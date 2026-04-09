"""
Shared wardrobe models.

A SharedWardrobe is a collaborative bucket of clothing items that multiple
users can contribute to. Items live in the shared wardrobe — they are not
references to any user's personal ClothingItem, keeping personal wardrobes
private.

Membership roles:
  - owner  : the creator. Can invite/remove anyone, delete the wardrobe.
  - editor : can add/remove their own items.
  - viewer : read-only (not used yet, but reserved for later).
"""
from django.conf import settings
from django.db import models


class MemberRole(models.TextChoices):
    OWNER  = 'owner',  'Owner'
    EDITOR = 'editor', 'Editor'
    VIEWER = 'viewer', 'Viewer'


class SharedWardrobe(models.Model):
    name        = models.CharField(max_length=120)
    description = models.CharField(max_length=500, blank=True)
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shared_wardrobes_created',
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    def is_member(self, user) -> bool:
        return self.members.filter(user=user).exists()

    def member_role(self, user):
        member = self.members.filter(user=user).first()
        return member.role if member else None


class SharedWardrobeMember(models.Model):
    wardrobe  = models.ForeignKey(
        SharedWardrobe,
        on_delete=models.CASCADE,
        related_name='members',
    )
    user      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shared_wardrobe_memberships',
    )
    role      = models.CharField(
        max_length=10,
        choices=MemberRole.choices,
        default=MemberRole.EDITOR,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['wardrobe', 'user'], name='unique_wardrobe_member'),
        ]

    def __str__(self):
        return f'{self.user_id} in {self.wardrobe_id} ({self.role})'


class SharedWardrobeItem(models.Model):
    CATEGORY_CHOICES = [
        ('top',        'Top'),
        ('bottom',     'Bottom'),
        ('dress',      'Dress'),
        ('outerwear',  'Outerwear'),
        ('footwear',   'Footwear'),
        ('accessory',  'Accessory'),
        ('other',      'Other'),
    ]

    wardrobe    = models.ForeignKey(
        SharedWardrobe,
        on_delete=models.CASCADE,
        related_name='items',
    )
    added_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='shared_items_added',
    )
    name        = models.CharField(max_length=200)
    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    brand       = models.CharField(max_length=100, blank=True)
    image_url   = models.URLField(blank=True)
    notes       = models.CharField(max_length=500, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wardrobe', '-created_at']),
        ]

    def __str__(self):
        return f'{self.name} ({self.wardrobe_id})'
