from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers as drf_serializers
from drf_spectacular.types import OpenApiTypes
from .weather import get_weather, get_weather_for_location


@extend_schema(
    summary="Get weather forecast",
    description="Fetch a weather snapshot for a location by lat/lon or name. Free, no API key required.",
    parameters=[
        OpenApiParameter('lat',      OpenApiTypes.FLOAT,  description='Latitude'),
        OpenApiParameter('lon',      OpenApiTypes.FLOAT,  description='Longitude'),
        OpenApiParameter('location', OpenApiTypes.STR,    description='Location name (geocoded)'),
        OpenApiParameter('date',     OpenApiTypes.DATE,   description='Date (defaults to today)'),
    ],
)
class WeatherView(APIView):
    """
    GET /api/weather/?lat=47.37&lon=8.54
    GET /api/weather/?location=Zurich
    GET /api/weather/?location=Tokyo&date=2026-04-01
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get live weather forecast",
        description="Fetch weather snapshot by ?lat=&lon= or ?location=. Free, no API key.",
        responses={200: inline_serializer(name='WeatherSnapshot', fields={
            'temp_c': __import__('rest_framework').serializers.FloatField(),
            'condition': __import__('rest_framework').serializers.CharField(),
            'precipitation_probability': __import__('rest_framework').serializers.IntegerField(),
            'is_raining': __import__('rest_framework').serializers.BooleanField(),
            'source': __import__('rest_framework').serializers.CharField(),
        })},
    )
    def get(self, request):
        import datetime

        date_str = request.query_params.get('date')
        date = None
        if date_str:
            try:
                date = datetime.date.fromisoformat(date_str)
            except ValueError:
                return Response({'detail': 'Invalid date. Use YYYY-MM-DD.'}, status=400)

        lat = request.query_params.get('lat')
        lon = request.query_params.get('lon')
        location = request.query_params.get('location')

        if lat and lon:
            try:
                snapshot = get_weather(float(lat), float(lon), date)
            except ValueError:
                return Response({'detail': 'Invalid lat/lon.'}, status=400)
        elif location:
            snapshot = get_weather_for_location(location, date)
        else:
            return Response(
                {'detail': 'Provide ?lat=&lon= or ?location= query parameter.'},
                status=400
            )

        return Response(snapshot)
