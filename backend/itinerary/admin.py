from django.contrib import admin
from .models import CalendarEvent, Trip


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display  = ['title', 'user', 'event_type', 'start_time', 'source']
    list_filter   = ['event_type', 'source']
    search_fields = ['title', 'user__email', 'location']


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display  = ['name', 'user', 'destination', 'start_date', 'end_date']
    search_fields = ['name', 'user__email', 'destination']
