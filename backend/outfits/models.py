from django.db import models
from django.conf import settings


class OutfitRecommendation(models.Model):
    SOURCE_CHOICES = [
        ('daily',  'Daily Look'),
        ('trip',   'Trip Planner'),
        ('manual', 'Manual'),
    ]

    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='outfit_recommendations')
    date        = models.DateField()
    source      = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='daily')
    event       = models.ForeignKey('itinerary.CalendarEvent', null=True, blank=True, on_delete=models.SET_NULL)
    trip        = models.ForeignKey('itinerary.Trip', null=True, blank=True, on_delete=models.SET_NULL)
    items       = models.ManyToManyField('wardrobe.ClothingItem', through='OutfitItem')
    notes       = models.TextField(blank=True)           # AI explanation
    weather_snapshot = models.JSONField(default=dict, blank=True)
    accepted    = models.BooleanField(null=True)         # None=unseen, True=accepted, False=rejected
    points_awarded = models.BooleanField(default=False)   # prevents double-awarding sustainability points
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        indexes  = [
            models.Index(fields=['user', 'date'], name='outfit_user_date_idx'),
            models.Index(fields=['user', 'source'], name='outfit_user_source_idx'),
        ]

    def __str__(self):
        return f'{self.user.email} — outfit {self.date}'


class OutfitItem(models.Model):
    ROLE_CHOICES = [
        ('main',  'Main Piece'),
        ('layer', 'Layer'),
        ('shoes', 'Shoes'),
        ('bag',   'Bag'),
        ('other', 'Other'),
    ]

    outfit       = models.ForeignKey(OutfitRecommendation, on_delete=models.CASCADE)
    clothing_item = models.ForeignKey('wardrobe.ClothingItem', on_delete=models.CASCADE)
    role         = models.CharField(max_length=10, choices=ROLE_CHOICES, default='main')
    liked        = models.BooleanField(null=True)

    class Meta:
        unique_together = ('outfit', 'clothing_item')
