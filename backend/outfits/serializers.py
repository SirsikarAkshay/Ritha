from rest_framework import serializers
from .models import OutfitRecommendation, OutfitItem


class OutfitItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='clothing_item.name', read_only=True)
    item_category = serializers.CharField(source='clothing_item.category', read_only=True)
    item_brand = serializers.CharField(source='clothing_item.brand', read_only=True)
    item_colors = serializers.JSONField(source='clothing_item.colors', read_only=True)

    class Meta:
        model  = OutfitItem
        fields = ['clothing_item', 'role', 'liked', 'item_name', 'item_category', 'item_brand', 'item_colors']


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
