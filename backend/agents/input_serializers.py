"""
Input validation serializers for agent endpoints.
Each serializer validates and documents the expected POST body.
"""

from rest_framework import serializers


class WeatherInputMixin(serializers.Serializer):
    """Optional weather override — if omitted, live weather is fetched."""

    lat = serializers.FloatField(required=False, help_text="Latitude for live weather")
    lon = serializers.FloatField(required=False, help_text="Longitude for live weather")
    location = serializers.CharField(required=False, allow_blank=True, help_text="Location name (geocoded)")
    weather = serializers.DictField(required=False, help_text="Weather snapshot dict (overrides live fetch)")

    def validate(self, data):
        # lat+lon must come together
        if ("lat" in data) != ("lon" in data):
            raise serializers.ValidationError("Provide both `lat` and `lon`, or neither.")
        return data


class DailyLookInputSerializer(WeatherInputMixin):
    """Input for POST /api/agents/daily-look/"""

    # No additional required fields — calendar + wardrobe are pulled from DB


class WeeklyLooksInputSerializer(WeatherInputMixin):
    """Input for POST /api/agents/weekly-looks/"""

    # No additional required fields — generates 7 days from today


class PackingListInputSerializer(WeatherInputMixin):
    """Input for POST /api/agents/packing-list/"""

    # Preset bag sizes → liters, used when bag_capacity_liters is omitted.
    BAG_TYPE_LITERS = {
        "personal_item": 20,
        "backpack": 30,
        "carry_on": 40,
        "checked": 70,
    }

    days = serializers.IntegerField(
        required=False, default=3, min_value=1, max_value=30, help_text="Trip duration in days"
    )
    activities = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list,
        help_text='List of activity types, e.g. ["beach", "hiking", "dinner"]',
    )
    bag_capacity_liters = serializers.IntegerField(
        required=False,
        min_value=5,
        max_value=200,
        help_text="Bag volume in liters (e.g. 30 for a 30L backpack). Omit for an unconstrained list.",
    )
    bag_type = serializers.ChoiceField(
        choices=["personal_item", "backpack", "carry_on", "checked"],
        required=False,
        help_text="Preset bag size, mapped to liters when bag_capacity_liters is not given.",
    )

    def validate(self, data):
        data = super().validate(data)
        # Resolve a preset bag_type into liters unless an explicit capacity was given.
        if "bag_capacity_liters" not in data and data.get("bag_type"):
            data["bag_capacity_liters"] = self.BAG_TYPE_LITERS[data["bag_type"]]
        return data


class OutfitPlannerInputSerializer(WeatherInputMixin):
    """Input for POST /api/agents/outfit-planner/"""

    trip_id = serializers.IntegerField(required=False, help_text="Existing Trip ID")
    start_date = serializers.DateField(required=False, help_text="Trip start date (YYYY-MM-DD)")
    end_date = serializers.DateField(required=False, help_text="Trip end date (YYYY-MM-DD)")
    destination = serializers.CharField(required=False, max_length=200, allow_blank=True)
    activities = serializers.ListField(child=serializers.CharField(max_length=50), required=False, default=list)

    def validate(self, data):
        data = super().validate(data)
        has_trip = "trip_id" in data
        has_dates = "start_date" in data and "end_date" in data
        if not has_trip and not has_dates:
            raise serializers.ValidationError("Provide either `trip_id` or both `start_date` and `end_date`.")
        if has_dates and data.get("start_date") and data.get("end_date"):
            if data["start_date"] > data["end_date"]:
                raise serializers.ValidationError("`start_date` must be before `end_date`.")
        return data


class ConflictDetectorInputSerializer(WeatherInputMixin):
    """Input for POST /api/agents/conflict-detector/"""

    date = serializers.DateField(required=False, help_text="Date to check (YYYY-MM-DD, defaults to today)")


class CulturalAdvisorInputSerializer(serializers.Serializer):
    """Input for POST /api/agents/cultural-advisor/"""

    country = serializers.CharField(max_length=100, help_text="Country name")
    city = serializers.CharField(max_length=100, required=False, default="", allow_blank=True)
    month = serializers.IntegerField(
        required=False, min_value=1, max_value=12, help_text="Month number 1-12 (defaults to current month)"
    )


class SmartRecommendInputSerializer(WeatherInputMixin):
    """Input for POST /api/agents/smart-recommend/"""

    destination = serializers.CharField(max_length=200, help_text='Destination city or country (e.g. "Tokyo", "Italy")')
    date = serializers.DateField(
        required=False, help_text="Date for the recommendation (YYYY-MM-DD, defaults to today)"
    )
    start_date = serializers.DateField(
        required=False, help_text="Trip start date (YYYY-MM-DD) — for multi-day recommendations"
    )
    end_date = serializers.DateField(
        required=False, help_text="Trip end date (YYYY-MM-DD) — for multi-day recommendations"
    )
    occasion = serializers.ChoiceField(
        choices=[
            "casual",
            "smart_casual",
            "business",
            "formal",
            "activewear",
            "travel",
            "cultural_visit",
            "date",
            "wedding",
            "interview",
        ],
        required=False,
        default="casual",
        help_text="Occasion type",
    )

    def validate(self, data):
        data = super().validate(data)
        if "start_date" in data and "end_date" in data:
            if data["start_date"] > data["end_date"]:
                raise serializers.ValidationError("`start_date` must be before `end_date`.")
        return data


class PlaceOutfitInputSerializer(WeatherInputMixin):
    """Input for POST /api/agents/place-outfit/ — an outfit for one specific place."""

    place = serializers.CharField(max_length=200, help_text="Name of the place to dress for")
    destination = serializers.CharField(
        max_length=200, help_text="City or country the place is in (drives weather + culture)"
    )
    date = serializers.DateField(required=False, help_text="Date (YYYY-MM-DD, defaults to today)")
    formality = serializers.ChoiceField(
        choices=["casual", "casual_smart", "smart", "formal"],
        required=False,
        default="casual_smart",
        help_text="Dress formality expected at the place",
    )
    place_type = serializers.CharField(
        required=False, allow_blank=True, help_text="landmark | religious | market | museum | nature | restaurant"
    )
    clothing_tip = serializers.CharField(
        required=False, allow_blank=True, help_text="Known dress note for the place (echoed back in the response)"
    )


class LuggageWeightInputSerializer(serializers.Serializer):
    """Input for POST /api/wardrobe/luggage-weight/"""

    item_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), min_length=1, help_text="List of ClothingItem IDs to weigh"
    )
    airline = serializers.ChoiceField(
        choices=["default", "easyjet", "ryanair", "swiss", "lufthansa", "ba"],
        required=False,
        default="default",
        help_text="Airline for carry-on limit comparison",
    )


class PublicTripInsightsInputSerializer(serializers.Serializer):
    """Unauthenticated instant-insight preview: destination-first, no wardrobe."""

    destination = serializers.CharField(max_length=200, help_text="City / country the user is travelling to")
    date = serializers.DateField(required=False, help_text="Trip start date (optional)")
    gender = serializers.ChoiceField(
        choices=[("men", "men"), ("women", "women"), ("kids", "kids")],
        required=False,
        default="women",
    )
    weather = serializers.DictField(required=False, help_text="Optional weather override (skips the live fetch)")
