from rest_framework import serializers
from .models import CulturalRule, LocalEvent


class CulturalRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model  = CulturalRule
        fields = '__all__'


class LocalEventSerializer(serializers.ModelSerializer):
    class Meta:
        model  = LocalEvent
        fields = '__all__'
