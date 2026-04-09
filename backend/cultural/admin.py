from django.contrib import admin
from .models import CulturalRule, LocalEvent


@admin.register(CulturalRule)
class CulturalRuleAdmin(admin.ModelAdmin):
    list_display  = ['country', 'city', 'place_name', 'rule_type', 'severity']
    list_filter   = ['rule_type', 'severity', 'country']
    search_fields = ['country', 'city', 'place_name', 'description']


@admin.register(LocalEvent)
class LocalEventAdmin(admin.ModelAdmin):
    list_display  = ['name', 'country', 'city', 'start_month', 'end_month']
    list_filter   = ['country']
    search_fields = ['name', 'country', 'city']
