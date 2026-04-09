from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email       = models.EmailField(unique=True)
    first_name  = models.CharField(max_length=100, blank=True)
    last_name   = models.CharField(max_length=100, blank=True)
    timezone    = models.CharField(max_length=64, default='UTC')
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    # Google Calendar OAuth tokens (stored as encrypted JSON)
    google_calendar_token      = models.TextField(blank=True)
    google_calendar_email      = models.EmailField(blank=True)   # the Google account email
    google_calendar_connected  = models.BooleanField(default=False)
    google_calendar_synced_at  = models.DateTimeField(null=True, blank=True)

    # Apple Calendar CalDAV credentials
    apple_calendar_username    = models.CharField(max_length=200, blank=True)  # Apple ID email
    apple_calendar_password    = models.TextField(blank=True)   # App-specific password (encrypted)
    apple_calendar_connected   = models.BooleanField(default=False)
    apple_calendar_synced_at   = models.DateTimeField(null=True, blank=True)

    # Microsoft Outlook / 365 Calendar
    outlook_calendar_token     = models.TextField(blank=True)
    outlook_calendar_email     = models.EmailField(blank=True)
    outlook_calendar_connected = models.BooleanField(default=False)
    outlook_calendar_synced_at = models.DateTimeField(null=True, blank=True)

    # Email verification
    is_email_verified        = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=64, blank=True)
    email_token_created_at   = models.DateTimeField(null=True, blank=True)

    # Password reset
    password_reset_token      = models.CharField(max_length=64, blank=True)
    password_reset_created_at = models.DateTimeField(null=True, blank=True)

    # Location preference for weather (used by daily look)
    location_name = models.CharField(max_length=200, blank=True, default='')  # e.g. 'Zurich'
    location_lat  = models.FloatField(null=True, blank=True)
    location_lon  = models.FloatField(null=True, blank=True)

    # Push notifications (Firebase Cloud Messaging)
    device_push_token   = models.TextField(blank=True)   # FCM token from mobile app
    push_notifications  = models.BooleanField(default=True)  # user opt-in

    # Style preferences
    style_profile = models.JSONField(default=dict, blank=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email
