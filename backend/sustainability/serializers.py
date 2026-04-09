from rest_framework import serializers
from .models import SustainabilityLog, UserSustainabilityProfile


class SustainabilityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SustainabilityLog
        fields = '__all__'
        read_only_fields = ['user', 'created_at']


class UserSustainabilityProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UserSustainabilityProfile
        fields = '__all__'
        read_only_fields = ['user', 'updated_at']
