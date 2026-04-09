from django.contrib import admin
from .models import SustainabilityLog, UserSustainabilityProfile


@admin.register(SustainabilityLog)
class SustainabilityLogAdmin(admin.ModelAdmin):
    list_display  = ['user', 'action', 'co2_saved_kg', 'points', 'created_at']
    list_filter   = ['action']
    search_fields = ['user__email']


@admin.register(UserSustainabilityProfile)
class UserSustainabilityProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'total_points', 'total_co2_saved_kg', 'wear_again_streak']
    search_fields = ['user__email']
