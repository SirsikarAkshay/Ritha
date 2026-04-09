from django.contrib import admin
from .models import ClothingItem


@admin.register(ClothingItem)
class ClothingItemAdmin(admin.ModelAdmin):
    list_display   = ['name', 'user', 'category', 'formality', 'season', 'times_worn', 'is_active']
    list_filter    = ['category', 'formality', 'season', 'is_active']
    search_fields  = ['name', 'user__email', 'brand']
    readonly_fields= ['times_worn', 'last_worn', 'created_at', 'updated_at']
