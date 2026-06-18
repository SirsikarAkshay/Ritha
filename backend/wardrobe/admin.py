from django.contrib import admin

from .models import ClothingItem, RegionCluster, StarterPackApplication, StarterPackItem


@admin.register(ClothingItem)
class ClothingItemAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "category", "formality", "season", "source", "times_worn", "is_active"]
    list_filter = ["category", "formality", "season", "source", "is_active"]
    search_fields = ["name", "user__email", "brand"]
    readonly_fields = ["times_worn", "last_worn", "created_at", "updated_at"]


@admin.register(RegionCluster)
class RegionClusterAdmin(admin.ModelAdmin):
    list_display = ["code", "display_name", "climate_zone", "cultural_cluster"]
    search_fields = ["code", "display_name", "cultural_cluster"]
    list_filter = ["climate_zone", "cultural_cluster"]


@admin.register(StarterPackItem)
class StarterPackItemAdmin(admin.ModelAdmin):
    list_display = [
        "display_name",
        "region_cluster",
        "gender",
        "category",
        "prevalence_pct",
        "confidence",
        "is_default",
        "is_opt_in",
    ]
    list_filter = ["region_cluster", "gender", "category", "confidence", "is_default", "is_opt_in", "opt_in_group"]
    search_fields = ["display_name", "subcategory", "source_label"]
    list_editable = ["is_default"]
    readonly_fields = []
    fieldsets = (
        ("Demographic", {"fields": ("region_cluster", "gender")}),
        (
            "Garment",
            {
                "fields": (
                    "category",
                    "subcategory",
                    "display_name",
                    "default_colors",
                    "seasonality",
                    "formality",
                    "preview_image_url",
                    "sort_order",
                )
            },
        ),
        ("Evidence", {"fields": ("prevalence_pct", "source_label", "source_year", "source_url", "confidence")}),
        ("Visibility", {"fields": ("is_default", "is_opt_in", "opt_in_group")}),
    )


@admin.register(StarterPackApplication)
class StarterPackApplicationAdmin(admin.ModelAdmin):
    list_display = ["user", "region_cluster", "gender", "pack_version", "completed_at"]
    list_filter = ["region_cluster", "gender", "pack_version"]
    search_fields = ["user__email"]
    readonly_fields = [
        "user",
        "region_cluster",
        "gender",
        "proposed_items",
        "custom_added",
        "opt_ins",
        "pack_version",
        "completed_at",
    ]
