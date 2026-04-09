from django.db import models


class CulturalRule(models.Model):
    RULE_TYPE_CHOICES = [
        ('cover_head',       'Head Covering Required'),
        ('cover_shoulders',  'Shoulders Must Be Covered'),
        ('cover_knees',      'Knees Must Be Covered'),
        ('no_bare_feet',     'No Bare Feet'),
        ('modest_dress',     'Modest Dress Required'),
        ('remove_shoes',     'Remove Shoes'),
        ('festival_wear',    'Festival / Event Specific'),
        ('color_warning',    'Colour Significance'),
        ('general',          'General Etiquette'),
    ]

    country     = models.CharField(max_length=100)
    city        = models.CharField(max_length=100, blank=True)
    place_name  = models.CharField(max_length=200, blank=True)
    rule_type   = models.CharField(max_length=30, choices=RULE_TYPE_CHOICES)
    description = models.TextField()
    severity    = models.CharField(
        max_length=10,
        choices=[('info','Info'), ('warning','Warning'), ('required','Required')],
        default='info',
    )
    source_url  = models.URLField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['country', 'city']

    def __str__(self):
        return f'{self.country} — {self.rule_type}'


class LocalEvent(models.Model):
    country       = models.CharField(max_length=100)
    city          = models.CharField(max_length=100, blank=True)
    name          = models.CharField(max_length=200)
    description   = models.TextField()
    clothing_note = models.TextField(blank=True)
    start_month   = models.PositiveSmallIntegerField()
    end_month     = models.PositiveSmallIntegerField()
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['country', 'name']

    def __str__(self):
        return f'{self.name} ({self.country})'
