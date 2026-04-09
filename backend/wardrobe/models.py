from django.db import models
from django.conf import settings


class ClothingItem(models.Model):
    CATEGORY_CHOICES = [
        ('top',        'Top'),
        ('bottom',     'Bottom'),
        ('dress',      'Dress'),
        ('outerwear',  'Outerwear'),
        ('footwear',   'Footwear'),
        ('accessory',  'Accessory'),
        ('activewear', 'Activewear'),
        ('formal',     'Formal'),
        ('other',      'Other'),
    ]

    FORMALITY_CHOICES = [
        ('casual',       'Casual'),
        ('casual_smart', 'Casual Smart'),
        ('smart',        'Smart'),
        ('formal',       'Formal'),
        ('activewear',   'Activewear'),
    ]

    SEASON_CHOICES = [
        ('spring', 'Spring'),
        ('summer', 'Summer'),
        ('autumn', 'Autumn'),
        ('winter', 'Winter'),
        ('all',    'All Season'),
    ]

    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wardrobe')
    name        = models.CharField(max_length=200)
    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    formality   = models.CharField(max_length=20, choices=FORMALITY_CHOICES, default='casual')
    season      = models.CharField(max_length=10, choices=SEASON_CHOICES, default='all')
    colors      = models.JSONField(default=list)          # ['navy', 'white']
    material    = models.CharField(max_length=100, blank=True)
    weight_grams = models.PositiveIntegerField(null=True, blank=True)
    brand       = models.CharField(max_length=100, blank=True)
    image       = models.ImageField(upload_to='wardrobe/', blank=True, null=True)
    image_clean = models.ImageField(upload_to='wardrobe/clean/', blank=True, null=True)  # bg-removed
    tags        = models.JSONField(default=list)           # ['office', 'travel', 'date']
    is_active   = models.BooleanField(default=True)        # soft-delete
    times_worn  = models.PositiveIntegerField(default=0)
    last_worn   = models.DateField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} — {self.name}'
