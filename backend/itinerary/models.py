from django.db import models
from django.conf import settings


class CalendarEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('external_meeting', 'External Meeting / Client'),
        ('internal_meeting', 'Internal Meeting / Standup'),
        ('workout',          'Gym / Workout'),
        ('social',           'Social / Dinner'),
        ('travel',           'Travel Day'),
        ('free',             'Nothing Scheduled'),
        ('wedding',          'Wedding / Ceremony'),
        ('interview',        'Interview'),
        ('date',             'Date'),
        ('other',            'Other'),
    ]

    SOURCE_CHOICES = [
        ('google',  'Google Calendar'),
        ('outlook', 'Outlook'),
        ('apple',   'Apple Calendar'),
        ('device',  'Device Calendar'),
        ('manual',  'Manual Entry'),
    ]

    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='events')
    title       = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    location    = models.CharField(max_length=500, blank=True)
    event_type  = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES, default='other')
    formality   = models.CharField(max_length=20, blank=True)
    start_time  = models.DateTimeField()
    end_time    = models.DateTimeField()
    all_day     = models.BooleanField(default=False)
    source      = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='manual')
    external_id = models.CharField(max_length=500, blank=True)
    raw_data    = models.JSONField(default=dict, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_time']
        indexes  = [models.Index(fields=['user', 'start_time'])]

    def save(self, *args, **kwargs):
        # Auto-classify if event_type is still 'other' and title is provided
        if self.title and self.event_type == 'other':
            from ritha.services.event_classifier import classify_event
            result = classify_event(self.title, self.description)
            self.event_type = result['event_type']
            if not self.formality:
                self.formality = result['formality']
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.email} — {self.title} ({self.start_time.date()})'


class Trip(models.Model):
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trips')
    shared_wardrobe = models.ForeignKey(
        'shared_wardrobe.SharedWardrobe', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='trips',
    )
    name        = models.CharField(max_length=200)
    destination = models.CharField(max_length=400)
    # Structured destination. `country` is the trip's country, `cities` is a list
    # of cities/towns inside that country (multi-city trips). `destination` is
    # auto-derived on save for backward compatibility with older code paths.
    country     = models.CharField(max_length=120, blank=True, default='')
    cities      = models.JSONField(default=list, blank=True)
    start_date  = models.DateField()
    end_date    = models.DateField()
    notes       = models.TextField(blank=True)
    saved_recommendation = models.JSONField(null=True, blank=True, default=None)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']

    def save(self, *args, **kwargs):
        # Keep `destination` in sync with structured fields when provided.
        if self.country or self.cities:
            parts = [c for c in (self.cities or []) if c] + ([self.country] if self.country else [])
            derived = ', '.join(parts)
            if derived:
                self.destination = derived[:400]
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.email} — {self.name}'


class PackingChecklistItem(models.Model):
    """
    A single item on a trip's packing checklist.
    Linked to a wardrobe ClothingItem or free-text if item not in wardrobe.
    """
    trip            = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='checklist_items')
    clothing_item   = models.ForeignKey(
        'wardrobe.ClothingItem', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='checklist_entries',
    )
    custom_name     = models.CharField(max_length=200, blank=True)  # fallback if no wardrobe item
    is_packed       = models.BooleanField(default=False)
    quantity        = models.PositiveSmallIntegerField(default=1)
    notes           = models.CharField(max_length=300, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['is_packed', 'created_at']

    @property
    def display_name(self):
        if self.clothing_item:
            return self.clothing_item.name
        return self.custom_name or 'Unnamed item'

    def __str__(self):
        status = '✓' if self.is_packed else '○'
        return f'{status} {self.display_name} (Trip #{self.trip_id})'
