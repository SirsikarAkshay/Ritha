from rest_framework import serializers
from .models import AgentJob


class AgentJobSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AgentJob
        fields = '__all__'
        read_only_fields = ['user', 'status', 'output_data', 'error', 'created_at', 'completed_at']
