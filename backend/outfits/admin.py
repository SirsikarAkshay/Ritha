from django.contrib import admin
from .models import OutfitRecommendation, OutfitItem


class OutfitItemInline(admin.TabularInline):
    model = OutfitItem
    extra = 0


@admin.register(OutfitRecommendation)
class OutfitRecommendationAdmin(admin.ModelAdmin):
    list_display  = ['user', 'date', 'source', 'accepted', 'created_at']
    list_filter   = ['source', 'accepted']
    inlines       = [OutfitItemInline]
