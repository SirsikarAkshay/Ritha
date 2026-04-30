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


class UserStyleProfile(models.Model):
    """Per-user learned preferences (§2.1).

    Persisted as flat JSON so it can be rebuilt cheaply from feedback history
    without schema migrations. Rebuilt nightly by a Celery task.

    Fields:
        category_pair_weights — {"top|bottom": 1.05, "top|outerwear": 0.92, ...}
            Multiplicative bias on the global co-occurrence score for a pair
            of categories, learned from this user's accept/reject history.
            1.0 = neutral; >1 = user likes this combo; <1 = user rejects it.
        item_pair_negatives — [[item_id_a, item_id_b], ...]
            Specific item pairs the user has consistently rejected. Hard
            soft-down-rank at scoring time.
        color_affinities — {"navy": 1.1, "neon": 0.7, ...}
            Per-color bias from items the user has liked / wears often.
        formality_distribution — {"casual": 0.6, "smart": 0.3, ...}
            Estimated distribution of the user's wardrobe by formality.
            Used as a prior so e.g. a casual-only user isn't shown formal
            recs unless an event forces it.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        # NOTE: NOT 'style_profile' — User already has a JSONField named
        # `style_profile` (free-form preferences set by signals.py and
        # wardrobe/views.py). Using the same related_name made Django
        # try to assign the JSONField's default `{}` through the reverse
        # one-to-one descriptor at startup and crash check_user_model.
        related_name='learned_style',
    )
    category_pair_weights  = models.JSONField(default=dict, blank=True)
    item_pair_negatives    = models.JSONField(default=list, blank=True)
    color_affinities       = models.JSONField(default=dict, blank=True)
    formality_distribution = models.JSONField(default=dict, blank=True)

    feedback_count = models.PositiveIntegerField(default=0)
    last_rebuilt   = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'StyleProfile<{self.user.email}>'
