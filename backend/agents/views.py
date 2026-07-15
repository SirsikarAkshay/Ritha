import datetime
import json

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers, views
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from . import services
from .input_serializers import (
    ConflictDetectorInputSerializer,
    CulturalAdvisorInputSerializer,
    DailyLookInputSerializer,
    OutfitPlannerInputSerializer,
    PackingListInputSerializer,
    PlaceOutfitInputSerializer,
    PublicTripInsightsInputSerializer,
    SmartRecommendInputSerializer,
    WeeklyLooksInputSerializer,
)
from .models import AgentJob
from .throttles import AIAgentThrottle


def _agent_schema(name: str):
    return inline_serializer(
        name=name,
        fields={
            "job_id": serializers.IntegerField(),
            "status": serializers.CharField(),
            "output": serializers.DictField(child=serializers.JSONField()),
        },
    )


class BaseAgentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [AIAgentThrottle]
    serializer_class = None
    input_serializer_class = None
    agent_type: str = ""

    def _run(self, request):
        # Validate input if a serializer is defined
        if self.input_serializer_class:
            input_ser = self.input_serializer_class(data=request.data)
            input_ser.is_valid(raise_exception=True)
            validated = input_ser.validated_data
        else:
            validated = request.data

        # Serialize input_data safely (validated_data may contain date objects)
        safe_input = json.loads(json.dumps(dict(request.data), default=str))
        job = AgentJob.objects.create(
            user=request.user,
            agent_type=self.agent_type,
            input_data=safe_input,
            status="running",
        )
        try:
            output = self.run(request.user, validated)
            job.status = "completed"
            job.output_data = output
            job.completed_at = datetime.datetime.now(tz=datetime.UTC)
            job.save()
            return Response({"job_id": job.id, "status": "completed", "output": output})
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            job.save()
            return Response({"job_id": job.id, "status": "failed", "error": str(exc)}, status=500)

    def run(self, user, data):
        raise NotImplementedError


class DailyLookView(BaseAgentView):
    agent_type = "daily_look"
    input_serializer_class = DailyLookInputSerializer

    @extend_schema(
        summary="Generate today's daily outfit",
        request=DailyLookInputSerializer,
        responses={200: _agent_schema("DailyLookResponse")},
        description=(
            "Analyses today's calendar events and weather then selects the best outfit "
            "from the user's wardrobe. Persists an OutfitRecommendation record."
        ),
    )
    def post(self, request):
        return self._run(request)

    def run(self, user, data):
        return services.run_daily_look(user, data)


class WeeklyLooksView(BaseAgentView):
    agent_type = "weekly_looks"
    input_serializer_class = WeeklyLooksInputSerializer

    @extend_schema(
        summary="Generate a full week of daily outfits",
        request=WeeklyLooksInputSerializer,
        responses={200: _agent_schema("WeeklyLooksResponse")},
        description=(
            "Generates 7 days of unique outfits based on weather forecasts and "
            "calendar events. Tracks used items across days to maximize variety."
        ),
    )
    def post(self, request):
        return self._run(request)

    def run(self, user, data):
        return services.run_weekly_looks(user, data)


class PackingListView(BaseAgentView):
    agent_type = "packing_list"
    input_serializer_class = PackingListInputSerializer

    @extend_schema(
        summary="Generate a packing list for a trip",
        request=PackingListInputSerializer,
        responses={200: _agent_schema("PackingListResponse")},
        description="Uses the 5-4-3-2-1 capsule rule. Pass `days` (int) and `activities` (list).",
    )
    def post(self, request):
        return self._run(request)

    def run(self, user, data):
        return services.run_packing_list(user, data)


class OutfitPlannerView(BaseAgentView):
    agent_type = "outfit_planner"
    input_serializer_class = OutfitPlannerInputSerializer

    @extend_schema(
        summary="Plan outfits for every day of a trip",
        request=OutfitPlannerInputSerializer,
        responses={200: _agent_schema("OutfitPlannerResponse")},
        description="Returns a per-day outfit plan. Pass `trip_id` or `start_date`/`end_date`/`destination`.",
    )
    def post(self, request):
        return self._run(request)

    def run(self, user, data):
        return services.run_outfit_planner(user, data)


class ConflictDetectorView(BaseAgentView):
    agent_type = "conflict_detector"
    input_serializer_class = ConflictDetectorInputSerializer

    @extend_schema(
        summary="Detect outfit/weather/schedule conflicts",
        request=ConflictDetectorInputSerializer,
        responses={200: _agent_schema("ConflictDetectorResponse")},
        description="Checks calendar events against weather. Pass `date` (YYYY-MM-DD) and optionally `lat`/`lon`.",
    )
    def post(self, request):
        return self._run(request)

    def run(self, user, data):
        return services.run_conflict_detector(user, data)


class CulturalAdvisorView(BaseAgentView):
    agent_type = "cultural_advisor"
    input_serializer_class = CulturalAdvisorInputSerializer

    @extend_schema(
        summary="Get cultural clothing advice for a destination",
        request=CulturalAdvisorInputSerializer,
        responses={200: _agent_schema("CulturalAdvisorResponse")},
        description="Returns etiquette rules and local event clothing notes. Pass `country`, optional `city` and `month`.",
    )
    def post(self, request):
        return self._run(request)

    def run(self, user, data):
        return services.run_cultural_advisor(user, data)


class SmartRecommendView(BaseAgentView):
    agent_type = "smart_recommend"
    input_serializer_class = SmartRecommendInputSerializer

    @extend_schema(
        summary="Unified smart outfit recommendation",
        request=SmartRecommendInputSerializer,
        responses={200: _agent_schema("SmartRecommendResponse")},
        description=(
            "Combines the trained fashion ML model, live weather data, and "
            "Mistral-powered cultural intelligence to produce outfit recommendations. "
            "Items found in the user's wardrobe are returned directly; gaps include "
            "shopping links. Pass `destination` (required), optional `date`, `occasion`."
        ),
    )
    def post(self, request):
        return self._run(request)

    def run(self, user, data):
        return services.run_smart_recommend(user, data)


class PlaceOutfitView(BaseAgentView):
    agent_type = "place_outfit"
    input_serializer_class = PlaceOutfitInputSerializer

    @extend_schema(
        summary="Outfit for a specific place",
        request=PlaceOutfitInputSerializer,
        responses={200: _agent_schema("PlaceOutfitResponse")},
        description=(
            "Builds an outfit for one place (e.g. a mosque, a rooftop bar) by mapping "
            "the place's dress formality to an occasion and running the recommendation "
            "engine under that destination's weather + culture. Returns wardrobe_matches "
            "(with item images), notes, and shopping suggestions for gaps."
        ),
    )
    def post(self, request):
        return self._run(request)

    def run(self, user, data):
        return services.run_place_outfit(user, data)


class PublicTripInsightsView(views.APIView):
    """Unauthenticated 'instant insight' — the destination-first onboarding hook.

    Given only a destination (+ optional date), returns weather, cultural
    dress-code alerts, places to visit, a standard packing capsule, and a gap
    analysis — with NO account and NO wardrobe, so a visitor gets the payoff
    before signing up. The capsule is clearly labelled as generic (see
    `capsule_note`); personalisation happens after they create an account.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []  # public — never require/parse a token
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        summary="Public destination insights (no auth)",
        description="Weather + dress code + places + a standard packing capsule + gap analysis for a destination.",
        request=PublicTripInsightsInputSerializer,
        responses={
            200: inline_serializer(name="PublicTripInsightsResponse", fields={"output": serializers.DictField()})
        },
    )
    def post(self, request):
        from ritha.services.public_insights import trip_insights

        ser = PublicTripInsightsInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        output = trip_insights(
            destination=d["destination"],
            date=d["date"].isoformat() if d.get("date") else None,
            gender=d.get("gender", "women"),
            weather=d.get("weather"),
            home_city=d.get("home_city"),
            home_temp_c=d.get("home_temp_c"),
        )
        return Response({"output": output})
