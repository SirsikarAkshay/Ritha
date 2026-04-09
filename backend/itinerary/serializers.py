from rest_framework import serializers
from .models import CalendarEvent, Trip, PackingChecklistItem


class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CalendarEvent
        fields = '__all__'
        read_only_fields = ['user', 'created_at']


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Trip
        fields = '__all__'
        read_only_fields = ['user', 'created_at']


class PackingChecklistItemSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model  = PackingChecklistItem
        fields = [
            'id', 'trip', 'clothing_item', 'custom_name', 'display_name',
            'is_packed', 'quantity', 'notes', 'created_at',
        ]
        read_only_fields = ['created_at', 'display_name']
