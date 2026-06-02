from rest_framework import serializers
from .models import ClothingItem, RegionCluster, StarterPackItem, StarterPackApplication


class ClothingItemSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ClothingItem
        # `embedding` is an internal binary feature vector — never expose it in
        # the API (it would bloat every response as base64 and leaks internals).
        exclude = ['embedding']
        read_only_fields = ['user', 'times_worn', 'last_worn', 'created_at', 'updated_at']


class RegionClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model  = RegionCluster
        fields = ['code', 'display_name', 'climate_zone', 'cultural_cluster',
                  'country_codes', 'notes']


class StarterPackItemSerializer(serializers.ModelSerializer):
    """Read-only catalog row, exposed to clients with the full evidence trail."""
    class Meta:
        model  = StarterPackItem
        fields = [
            'id', 'category', 'subcategory', 'display_name',
            'default_colors', 'seasonality', 'formality',
            'prevalence_pct', 'source_label', 'source_year', 'source_url',
            'confidence', 'is_default', 'is_opt_in', 'opt_in_group',
            'preview_image_url', 'sort_order',
        ]


class StarterPackPreviewSerializer(serializers.Serializer):
    """Bundle of the proposed pack for a (region, gender) request."""
    region   = RegionClusterSerializer()
    gender   = serializers.CharField()
    items    = StarterPackItemSerializer(many=True)
    opt_in_groups = serializers.ListField(child=serializers.CharField())


class StarterPackApplyRequestSerializer(serializers.Serializer):
    """Body of POST /api/wardrobe/starter-pack/apply/"""
    region_code     = serializers.CharField()
    gender          = serializers.ChoiceField(choices=StarterPackItem.GENDER_CHOICES)
    accepted_ids    = serializers.ListField(child=serializers.IntegerField(), default=list)
    rejected_ids    = serializers.ListField(child=serializers.IntegerField(), default=list)
    opt_ins         = serializers.ListField(child=serializers.CharField(), default=list)
    custom_added    = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField()),
        default=list,
        help_text='Optional items the user typed in: [{"name":"...", "category":"top"}]',
    )


class StarterPackApplyResponseSerializer(serializers.Serializer):
    items_created   = serializers.IntegerField()
    application_id  = serializers.IntegerField()
