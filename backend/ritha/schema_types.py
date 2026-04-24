"""
Reusable drf-spectacular inline serializer types for APIView endpoints
that return free-form JSON (agents, weather, wardrobe utilities).
"""
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers


AgentOutputSchema = inline_serializer(
    name='AgentOutput',
    fields={
        'job_id':  serializers.IntegerField(),
        'status':  serializers.CharField(),
        'output':  serializers.DictField(),
    }
)

WeatherSchema = inline_serializer(
    name='WeatherSnapshot',
    fields={
        'temp_c':                    serializers.FloatField(),
        'temp_min_c':                serializers.FloatField(),
        'temp_max_c':                serializers.FloatField(),
        'condition':                 serializers.CharField(),
        'precipitation_probability': serializers.IntegerField(),
        'is_raining':                serializers.BooleanField(),
        'is_cold':                   serializers.BooleanField(),
        'is_hot':                    serializers.BooleanField(),
        'date':                      serializers.CharField(),
        'source':                    serializers.CharField(),
    }
)

LuggageWeightSchema = inline_serializer(
    name='LuggageWeight',
    fields={
        'total_grams':             serializers.IntegerField(),
        'total_kg':                serializers.FloatField(),
        'fits_carry_on':           serializers.BooleanField(),
        'co2_saved_vs_checked_kg': serializers.FloatField(),
        'tip':                     serializers.CharField(),
    }
)
