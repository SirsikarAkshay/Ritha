from rest_framework import serializers
from .models import OutfitRecommendation, OutfitItem


class OutfitItemSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OutfitItem
        fields = ['clothing_item', 'role']


class OutfitRecommendationSerializer(serializers.ModelSerializer):
    outfit_items = OutfitItemSerializer(source='outfititem_set', many=True, read_only=True)

    class Meta:
        model  = OutfitRecommendation
        fields = [
            'id', 'date', 'source', 'event', 'trip',
            'notes', 'weather_snapshot', 'accepted',
            'outfit_items', 'created_at',
        ]
        read_only_fields = ['created_at']
        # Explicitly exclude 'user' — never expose internal user FK in responses
