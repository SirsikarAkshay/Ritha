"""
Serializers for the social app.

- PublicUserSerializer: lightweight representation of a user for search results,
  connection lists, etc. Exposes the profile fields but never the email.
- MyProfileSerializer: the authenticated user's own profile, with write access
  to display_name / bio / avatar_url / visibility. Handle is read-only here;
  handle changes go through UpdateHandleSerializer (enforces cooldown).
- ConnectionSerializer: a Connection row with the "other" user inlined so the
  frontend doesn't need a second round-trip.
"""
import re
from datetime import timedelta

from django.utils import timezone as dj_timezone
from rest_framework import serializers

from .models import Profile, Connection, BlockedUser, ProfileVisibility

HANDLE_RE = re.compile(r'^[a-z0-9_]{3,30}$')
HANDLE_CHANGE_COOLDOWN_DAYS = 30


# ── Public user (handle + display_name + avatar + bio) ────────────────────

class PublicUserSerializer(serializers.Serializer):
    """
    Input: a User instance. Reads `.profile` to surface public fields.
    Respects profile visibility — if 'connections_only' and the viewer is
    not connected, bio is hidden.
    """
    id            = serializers.IntegerField(source='pk', read_only=True)
    handle        = serializers.SerializerMethodField()
    display_name  = serializers.SerializerMethodField()
    avatar_url    = serializers.SerializerMethodField()
    bio           = serializers.SerializerMethodField()
    visibility    = serializers.SerializerMethodField()

    def _profile(self, user):
        return getattr(user, 'profile', None)

    def get_handle(self, user):
        p = self._profile(user)
        return p.handle if p else ''

    def get_display_name(self, user):
        p = self._profile(user)
        return (p.display_name if p and p.display_name else user.first_name) or ''

    def get_avatar_url(self, user):
        p = self._profile(user)
        return p.avatar_url if p else ''

    def _viewer_is_connected(self, user):
        viewer = self.context.get('viewer')
        if not viewer or viewer.pk == user.pk:
            return True
        return Connection.are_connected(viewer, user)

    def get_bio(self, user):
        p = self._profile(user)
        if not p:
            return ''
        if p.visibility == ProfileVisibility.CONNECTIONS_ONLY and not self._viewer_is_connected(user):
            return ''
        return p.bio

    def get_visibility(self, user):
        p = self._profile(user)
        return p.visibility if p else ProfileVisibility.PUBLIC


# ── My profile (read + partial update) ────────────────────────────────────

class MyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Profile
        fields = [
            'handle', 'display_name', 'bio', 'avatar_url', 'visibility',
            'handle_changed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['handle', 'handle_changed_at', 'created_at', 'updated_at']


class UpdateHandleSerializer(serializers.Serializer):
    handle = serializers.CharField(max_length=30)

    def validate_handle(self, value):
        value = value.strip().lower()
        if not HANDLE_RE.match(value):
            raise serializers.ValidationError(
                'Handle must be 3–30 characters, lowercase letters, numbers, or underscores.'
            )
        profile = self.context['profile']
        if profile.handle == value:
            raise serializers.ValidationError('This is already your handle.')
        if Profile.objects.filter(handle=value).exclude(pk=profile.pk).exists():
            raise serializers.ValidationError('That handle is already taken.')

        if profile.handle_changed_at:
            age = dj_timezone.now() - profile.handle_changed_at
            if age < timedelta(days=HANDLE_CHANGE_COOLDOWN_DAYS):
                days_left = HANDLE_CHANGE_COOLDOWN_DAYS - age.days
                raise serializers.ValidationError(
                    f'You can only change your handle once every {HANDLE_CHANGE_COOLDOWN_DAYS} days. '
                    f'Try again in {days_left} day(s).'
                )
        return value


# ── Connection ────────────────────────────────────────────────────────────

class ConnectionSerializer(serializers.ModelSerializer):
    """
    Represents a connection from the viewer's perspective. `other_user`
    always points at the user who is NOT the viewer. `direction` tells the
    frontend whether the viewer sent or received this.
    """
    other_user = serializers.SerializerMethodField()
    direction  = serializers.SerializerMethodField()

    class Meta:
        model  = Connection
        fields = ['id', 'status', 'direction', 'other_user', 'created_at', 'updated_at']
        read_only_fields = fields

    def _viewer(self):
        return self.context['viewer']

    def get_direction(self, obj):
        return 'outgoing' if obj.from_user_id == self._viewer().pk else 'incoming'

    def get_other_user(self, obj):
        viewer = self._viewer()
        other = obj.to_user if obj.from_user_id == viewer.pk else obj.from_user
        return PublicUserSerializer(other, context={'viewer': viewer}).data


# ── Block ─────────────────────────────────────────────────────────────────

class BlockedUserSerializer(serializers.ModelSerializer):
    blocked_user = serializers.SerializerMethodField()

    class Meta:
        model  = BlockedUser
        fields = ['id', 'blocked_user', 'created_at']
        read_only_fields = fields

    def get_blocked_user(self, obj):
        return PublicUserSerializer(obj.blocked, context={'viewer': self.context.get('viewer')}).data
