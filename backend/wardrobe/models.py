from django.conf import settings
from django.db import models


class ClothingItem(models.Model):
    CATEGORY_CHOICES = [
        ("top", "Top"),
        ("bottom", "Bottom"),
        ("dress", "Dress"),
        ("outerwear", "Outerwear"),
        ("footwear", "Footwear"),
        ("accessory", "Accessory"),
        ("activewear", "Activewear"),
        ("formal", "Formal"),
        ("other", "Other"),
    ]

    FORMALITY_CHOICES = [
        ("casual", "Casual"),
        ("casual_smart", "Casual Smart"),
        ("smart", "Smart"),
        ("formal", "Formal"),
        ("activewear", "Activewear"),
    ]

    SEASON_CHOICES = [
        ("spring", "Spring"),
        ("summer", "Summer"),
        ("autumn", "Autumn"),
        ("winter", "Winter"),
        ("all", "All Season"),
    ]

    SOURCE_CHOICES = [
        ("manual", "Added manually"),
        ("starter_pack", "Auto-added from starter pack"),
        ("image_scan", "Detected from photo"),
        ("receipt", "Imported from receipt"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wardrobe")
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="manual")
    formality = models.CharField(max_length=20, choices=FORMALITY_CHOICES, default="casual")
    season = models.CharField(max_length=10, choices=SEASON_CHOICES, default="all")
    colors = models.JSONField(default=list)  # ['navy', 'white']
    material = models.CharField(max_length=100, blank=True)
    weight_grams = models.PositiveIntegerField(null=True, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to="wardrobe/", blank=True, null=True)
    image_clean = models.ImageField(upload_to="wardrobe/clean/", blank=True, null=True)  # bg-removed
    tags = models.JSONField(default=list)  # ['office', 'travel', 'date']
    is_active = models.BooleanField(default=True)  # soft-delete
    times_worn = models.PositiveIntegerField(default=0)
    last_worn = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Visual feature vector from ml.inference.get_embedding (MobileNetV2,
    # 1280 dims, float32). Stored as raw bytes (~5KB / item) and round-
    # tripped via numpy.frombuffer. Computed asynchronously by the
    # `compute_embeddings` management command — never blocking on upload.
    # When None, scorers fall back to the coarser 13×13 category matrix.
    embedding = models.BinaryField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} — {self.name}"


# ── Starter-pack catalog ──────────────────────────────────────────────────────
# Methodology (see CONTRIBUTING.md → "Starter packs"):
#   – Region buckets are climate × cultural cluster, not country-level.
#   – An item enters a pack iff prevalence ≥ 60%, OR ≥ 40% AND it's an
#     outfit anchor, OR ≥ 30% AND climate-mandatory.
#   – Religion-specific items are NEVER default; they're surfaced via
#     opt-in toggles at onboarding.
#   – Each item carries its source citation so the UI can show "owned by
#     N% of <demographic> per <survey>".


class RegionCluster(models.Model):
    """One of ~14 climate × cultural buckets. Seeded once via management cmd."""

    code = models.SlugField(unique=True, max_length=60)
    display_name = models.CharField(max_length=120)
    climate_zone = models.CharField(max_length=20)  # Köppen group: A/B/C/D/E
    cultural_cluster = models.CharField(max_length=40)  # 'south_asian', 'nw_european', ...
    country_codes = models.JSONField(default=list)  # ['IN-South','BD','SL','PK-South']
    notes = models.TextField(blank=True)  # methodology / audit trail

    def __str__(self):
        return self.display_name


class StarterPackItem(models.Model):
    """One catalog row, scoped to (region_cluster × gender)."""

    GENDER_CHOICES = [
        ("men", "Men"),
        ("women", "Women"),
        ("boys", "Boys"),
        ("girls", "Girls"),
        ("kid_boys", "Kid boys"),
        ("kid_girls", "Kid girls"),
    ]

    CONFIDENCE_CHOICES = [
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    ]

    region_cluster = models.ForeignKey(RegionCluster, on_delete=models.CASCADE, related_name="items")
    gender = models.CharField(max_length=12, choices=GENDER_CHOICES)

    # Garment classification (mirrors ClothingItem fields so we can copy across cleanly)
    category = models.CharField(max_length=20, choices=ClothingItem.CATEGORY_CHOICES)
    subcategory = models.CharField(max_length=60)  # 'kurta','oxford-shirt','sandals'
    display_name = models.CharField(max_length=120)
    default_colors = models.JSONField(default=list)  # ['navy','off-white']
    seasonality = models.CharField(max_length=10, choices=ClothingItem.SEASON_CHOICES, default="all")
    formality = models.CharField(max_length=20, choices=ClothingItem.FORMALITY_CHOICES, default="casual")

    # Statistical evidence trail — surfaced in the UI tooltip
    prevalence_pct = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    source_label = models.CharField(max_length=120)  # 'NSS Round 75 (urban India)'
    source_year = models.IntegerField(null=True, blank=True)
    source_url = models.URLField(blank=True)
    confidence = models.CharField(max_length=10, choices=CONFIDENCE_CHOICES, default="medium")

    # User-flow controls
    is_default = models.BooleanField(default=True)  # appears unless explicitly removed
    is_opt_in = models.BooleanField(default=False)  # religion / cultural — requires explicit toggle
    opt_in_group = models.CharField(max_length=40, blank=True)  # 'modest_dress','traditional','observant_jewish'

    # Stock image (Unsplash CDN URL during Phase 1; replaced with curated assets later)
    preview_image_url = models.URLField(blank=True)

    sort_order = models.IntegerField(default=0)

    class Meta:
        unique_together = [("region_cluster", "gender", "subcategory")]
        ordering = ["region_cluster", "gender", "sort_order", "-prevalence_pct"]

    def __str__(self):
        return f"{self.region_cluster.code}/{self.gender}/{self.subcategory}"


class StarterPackApplication(models.Model):
    """Telemetry: every onboarding decision feeds future pack refinement."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="starter_pack_application"
    )
    region_cluster = models.ForeignKey(RegionCluster, on_delete=models.PROTECT)
    gender = models.CharField(max_length=12)
    proposed_items = models.JSONField(default=list)  # [{subcategory, was_kept: bool}, ...]
    custom_added = models.JSONField(default=list)  # ['hijab','running shorts',...]
    opt_ins = models.JSONField(default=list)  # ['modest_dress','traditional']
    pack_version = models.IntegerField(default=1)  # bump when seed data changes
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.user.email} → {self.region_cluster.code}/{self.gender}"
