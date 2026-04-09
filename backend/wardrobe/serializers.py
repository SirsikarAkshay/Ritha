from rest_framework import serializers
from .models import ClothingItem


class ClothingItemSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ClothingItem
        fields = '__all__'
        read_only_fields = ['user', 'times_worn', 'last_worn', 'created_at', 'updated_at']
