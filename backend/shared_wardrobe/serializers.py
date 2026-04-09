from rest_framework import serializers

from social.serializers import PublicUserSerializer
from .models import SharedWardrobe, SharedWardrobeItem, SharedWardrobeMember


class SharedWardrobeItemSerializer(serializers.ModelSerializer):
    added_by = PublicUserSerializer(read_only=True)

    class Meta:
        model  = SharedWardrobeItem
        fields = ['id', 'wardrobe', 'added_by', 'name', 'category', 'brand',
                  'image_url', 'notes', 'created_at']
        read_only_fields = ['id', 'wardrobe', 'added_by', 'created_at']


class SharedWardrobeMemberSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)

    class Meta:
        model  = SharedWardrobeMember
        fields = ['id', 'user', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class SharedWardrobeSerializer(serializers.ModelSerializer):
    members   = SharedWardrobeMemberSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    my_role   = serializers.SerializerMethodField()

    class Meta:
        model  = SharedWardrobe
        fields = ['id', 'name', 'description', 'created_by', 'created_at',
                  'updated_at', 'members', 'item_count', 'my_role']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_item_count(self, obj):
        return obj.items.count()

    def get_my_role(self, obj):
        me = self.context['request'].user
        return obj.member_role(me)
