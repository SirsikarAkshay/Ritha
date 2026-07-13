from rest_framework import serializers

from .models import OutfitItem, OutfitRecommendation


class OutfitItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="clothing_item.name", read_only=True)
    item_category = serializers.CharField(source="clothing_item.category", read_only=True)
    item_brand = serializers.CharField(source="clothing_item.brand", read_only=True)
    item_colors = serializers.JSONField(source="clothing_item.colors", read_only=True)

    class Meta:
        model = OutfitItem
        fields = ["clothing_item", "role", "liked", "item_name", "item_category", "item_brand", "item_colors"]


class OutfitRecommendationSerializer(serializers.ModelSerializer):
    outfit_items = OutfitItemSerializer(source="outfititem_set", many=True, read_only=True)

    class Meta:
        model = OutfitRecommendation
        fields = [
            "id",
            "date",
            "source",
            "event",
            "trip",
            "notes",
            "weather_snapshot",
            "accepted",
            "outfit_items",
            "created_at",
        ]
        read_only_fields = ["created_at"]

    def _check_owned(self, obj, label):
        # `trip` and `event` are client-supplied writable FKs — don't let a user
        # attach their recommendation to another user's trip/event.
        if obj is None:
            return obj
        request = self.context.get("request")
        if request and getattr(obj, "user_id", None) != request.user.id:
            raise serializers.ValidationError(f"That {label} isn't yours.")
        return obj

    def validate_trip(self, value):
        return self._check_owned(value, "trip")

    def validate_event(self, value):
        return self._check_owned(value, "event")
