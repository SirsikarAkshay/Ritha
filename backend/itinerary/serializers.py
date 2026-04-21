from rest_framework import serializers
from .models import CalendarEvent, Trip, PackingChecklistItem


class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CalendarEvent
        fields = '__all__'
        read_only_fields = ['user', 'created_at']


class TripSerializer(serializers.ModelSerializer):
    shared_wardrobe_name = serializers.CharField(
        source='shared_wardrobe.name', read_only=True, default=None,
    )
    is_collaborative = serializers.SerializerMethodField()

    class Meta:
        model  = Trip
        fields = '__all__'
        read_only_fields = ['user', 'created_at']

    def get_is_collaborative(self, obj):
        return obj.shared_wardrobe_id is not None


class PackingChecklistItemSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model  = PackingChecklistItem
        fields = [
            'id', 'trip', 'clothing_item', 'custom_name', 'display_name',
            'is_packed', 'quantity', 'notes', 'created_at',
        ]
        read_only_fields = ['created_at', 'display_name']
