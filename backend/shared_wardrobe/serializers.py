from rest_framework import serializers
from social.serializers import PublicUserSerializer

from .models import SharedWardrobe, SharedWardrobeInvitation, SharedWardrobeItem, SharedWardrobeMember


class SharedWardrobeItemSerializer(serializers.ModelSerializer):
    added_by = PublicUserSerializer(read_only=True)
    claimed_by = PublicUserSerializer(read_only=True)

    class Meta:
        model = SharedWardrobeItem
        fields = [
            "id", "wardrobe", "added_by", "name", "category", "brand", "image_url", "notes",
            "claimed_by", "claimed_at", "created_at",
        ]
        read_only_fields = ["id", "wardrobe", "added_by", "claimed_by", "claimed_at", "created_at"]


class SharedWardrobeMemberSerializer(serializers.ModelSerializer):
    user = PublicUserSerializer(read_only=True)
    wardrobe_item_count = serializers.SerializerMethodField()

    class Meta:
        model = SharedWardrobeMember
        fields = ["id", "user", "role", "joined_at", "wardrobe_item_count"]
        read_only_fields = ["id", "joined_at", "wardrobe_item_count"]

    def get_wardrobe_item_count(self, obj):
        # Per-member personal wardrobe size — powers the reel's "Aditi · 26 items".
        from wardrobe.models import ClothingItem

        return ClothingItem.objects.filter(user_id=obj.user_id).count()


class SharedWardrobeSerializer(serializers.ModelSerializer):
    members = SharedWardrobeMemberSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    bag_savings = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()
    pending_invitee_ids = serializers.SerializerMethodField()

    class Meta:
        model = SharedWardrobe
        fields = [
            "id",
            "name",
            "description",
            "created_by",
            "created_at",
            "updated_at",
            "members",
            "item_count",
            "bag_savings",
            "my_role",
            "pending_invitee_ids",
            "invite_token",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at", "invite_token"]

    def get_item_count(self, obj):
        return obj.items.count()

    def get_bag_savings(self, obj):
        # {"saved_volume_l": float, "bags_saved": int} — the group's saved bag space.
        return obj.bag_savings()

    def get_my_role(self, obj):
        me = self.context["request"].user
        return obj.member_role(me)

    def get_pending_invitee_ids(self, obj):
        return list(obj.invitations.filter(status="pending").values_list("invitee_id", flat=True))


class SharedWardrobeInvitationSerializer(serializers.ModelSerializer):
    invited_by = PublicUserSerializer(read_only=True)
    invitee = PublicUserSerializer(read_only=True)
    wardrobe_name = serializers.CharField(source="wardrobe.name", read_only=True)

    class Meta:
        model = SharedWardrobeInvitation
        fields = ["id", "wardrobe", "wardrobe_name", "invited_by", "invitee", "status", "created_at", "resolved_at"]
        read_only_fields = ["id", "wardrobe", "invited_by", "invitee", "status", "created_at", "resolved_at"]
