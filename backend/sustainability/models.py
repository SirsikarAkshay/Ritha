from django.db import models
from django.conf import settings


class SustainabilityLog(models.Model):
    ACTION_CHOICES = [
        ('wear_again',      'Re-wore an item'),
        ('carry_on_only',   'Switched to carry-on'),
        ('weight_saved',    'Reduced luggage weight'),
        ('rental',          'Chose rental over purchase'),
        ('secondhand',      'Bought secondhand'),
    ]

    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sustainability_logs')
    action      = models.CharField(max_length=20, choices=ACTION_CHOICES)
    co2_saved_kg = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    points      = models.PositiveIntegerField(default=0)
    notes       = models.CharField(max_length=300, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['user', 'action'], name='sustlog_user_action_idx'),
        ]

    def __str__(self):
        return f'{self.user.email} — {self.action} (+{self.points} pts)'


class UserSustainabilityProfile(models.Model):
    user         = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sustainability_profile')
    total_points = models.PositiveIntegerField(default=0)
    total_co2_saved_kg = models.DecimalField(max_digits=8, decimal_places=3, default=0)
    wear_again_streak  = models.PositiveIntegerField(default=0)
    updated_at   = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.email} — {self.total_points} pts'
