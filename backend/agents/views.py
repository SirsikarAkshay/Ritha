import datetime
import json
from rest_framework import permissions, views, serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, inline_serializer
from .models import AgentJob
from .throttles import AIAgentThrottle
from .input_serializers import (
    DailyLookInputSerializer, PackingListInputSerializer,
    OutfitPlannerInputSerializer, ConflictDetectorInputSerializer,
    CulturalAdvisorInputSerializer,
)
from . import services


def _agent_schema(name: str):
    return inline_serializer(name=name, fields={
        'job_id': serializers.IntegerField(),
        'status': serializers.CharField(),
        'output': serializers.DictField(child=serializers.JSONField()),
    })


class BaseAgentView(views.APIView):
    permission_classes  = [permissions.IsAuthenticated]
    throttle_classes    = [AIAgentThrottle]
    serializer_class    = None
    input_serializer_class = None
    agent_type: str     = ''

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
            status='running',
        )
        try:
            output = self.run(request.user, validated)
            job.status       = 'completed'
            job.output_data  = output
            job.completed_at = datetime.datetime.now(tz=datetime.timezone.utc)
            job.save()
            return Response({'job_id': job.id, 'status': 'completed', 'output': output})
        except Exception as exc:
            job.status = 'failed'
            job.error  = str(exc)
            job.save()
            return Response({'job_id': job.id, 'status': 'failed', 'error': str(exc)}, status=500)

    def run(self, user, data):
        raise NotImplementedError


class DailyLookView(BaseAgentView):
    agent_type             = 'daily_look'
    input_serializer_class = DailyLookInputSerializer

    @extend_schema(
        summary="Generate today's daily outfit",
        request=DailyLookInputSerializer,
        responses={200: _agent_schema('DailyLookResponse')},
        description=(
            "Analyses today's calendar events and weather then selects the best outfit "
            "from the user's wardrobe. Persists an OutfitRecommendation record."
        ),
    )
    def post(self, request):
        return self._run(request)

    def run(self, user, data):
        return services.run_daily_look(user, data)


class PackingListView(BaseAgentView):
    agent_type             = 'packing_list'
    input_serializer_class = PackingListInputSerializer

    @extend_schema(
        summary="Generate a packing list for a trip",
        request=PackingListInputSerializer,
        responses={200: _agent_schema('PackingListResponse')},
        description="Uses the 5-4-3-2-1 capsule rule. Pass `days` (int) and `activities` (list).",
    )
    def post(self, request):
        return self._run(request)

    def run(self, user, data):
        return services.run_packing_list(user, data)


class OutfitPlannerView(BaseAgentView):
    agent_type             = 'outfit_planner'
    input_serializer_class = OutfitPlannerInputSerializer

    @extend_schema(
        summary="Plan outfits for every day of a trip",
        request=OutfitPlannerInputSerializer,
        responses={200: _agent_schema('OutfitPlannerResponse')},
        description="Returns a per-day outfit plan. Pass `trip_id` or `start_date`/`end_date`/`destination`.",
    )
    def post(self, request):
        return self._run(request)

    def run(self, user, data):
        return services.run_outfit_planner(user, data)


class ConflictDetectorView(BaseAgentView):
    agent_type             = 'conflict_detector'
    input_serializer_class = ConflictDetectorInputSerializer

    @extend_schema(
        summary="Detect outfit/weather/schedule conflicts",
        request=ConflictDetectorInputSerializer,
        responses={200: _agent_schema('ConflictDetectorResponse')},
        description="Checks calendar events against weather. Pass `date` (YYYY-MM-DD) and optionally `lat`/`lon`.",
    )
    def post(self, request):
        return self._run(request)

    def run(self, user, data):
        return services.run_conflict_detector(user, data)


class CulturalAdvisorView(BaseAgentView):
    agent_type             = 'cultural_advisor'
    input_serializer_class = CulturalAdvisorInputSerializer

    @extend_schema(
        summary="Get cultural clothing advice for a destination",
        request=CulturalAdvisorInputSerializer,
        responses={200: _agent_schema('CulturalAdvisorResponse')},
        description="Returns etiquette rules and local event clothing notes. Pass `country`, optional `city` and `month`.",
    )
    def post(self, request):
        return self._run(request)

    def run(self, user, data):
        return services.run_cultural_advisor(user, data)
