import logging

from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from rest_framework import parsers, permissions, serializers, status, viewsets
from rest_framework import views as drf_views
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from .models import ClothingItem, RegionCluster, StarterPackApplication, StarterPackItem
from .serializers import (
    ClothingItemSerializer,
    RegionClusterSerializer,
    StarterPackApplyRequestSerializer,
    StarterPackApplyResponseSerializer,
    StarterPackPreviewSerializer,
)

logger = logging.getLogger(__name__)


VALID_CATEGORIES = ["top", "bottom", "dress", "outerwear", "footwear", "accessory", "activewear", "formal", "other"]
VALID_FORMALITIES = ["casual", "casual_smart", "smart", "formal", "activewear"]
VALID_SEASONS = ["spring", "summer", "autumn", "winter", "all"]

ANALYZE_PROMPT = (
    "Analyze this clothing item photo and extract its details.\n"
    "Return JSON with exactly these keys:\n"
    '  - "name":      short descriptive name (e.g. "Navy cotton t-shirt")\n'
    f'  - "category":  one of {VALID_CATEGORIES}\n'
    f'  - "formality": one of {VALID_FORMALITIES}\n'
    f'  - "season":    one of {VALID_SEASONS} (use "all" if unsure)\n'
    '  - "colors":    list of 1-3 color names (lowercase)\n'
    '  - "material":  primary fabric if visible (e.g. "cotton", "denim"); empty string if unclear\n'
    '  - "brand":     visible brand name; empty string if not visible\n'
    '\nExample: {"name": "Navy cotton t-shirt", "category": "top", '
    '"formality": "casual", "season": "summer", "colors": ["navy"], '
    '"material": "cotton", "brand": ""}'
)


def _analyze_clothing_image(image_file):
    """Run vision analysis on an uploaded image and return a normalized dict.

    Returns (ok: bool, payload: dict). On failure, payload contains an `error` dict
    suitable for a DRF Response.
    """
    from ritha.services.mistral_client import _has_mistral, chat_image_json

    if not _has_mistral():
        return False, {
            "error": {
                "code": "not_configured",
                "message": "Image analysis is unavailable. MISTRAL_API_KEY is not set.",
            },
        }

    try:
        image_file.seek(0)
    except Exception:
        pass
    image_bytes = image_file.read()
    mime_type = getattr(image_file, "content_type", None) or "image/jpeg"

    try:
        result = chat_image_json(ANALYZE_PROMPT, image_bytes, mime_type)
    except Exception as exc:
        logger.warning("Clothing image analysis failed: %s", exc)
        return False, {
            "error": {
                "code": "analysis_failed",
                "message": "Could not analyze the image. Please try a clearer photo.",
            },
        }

    cat = result.get("category")
    form = result.get("formality")
    seas = result.get("season")
    cols = result.get("colors")

    cleaned = {
        "name": str(result.get("name") or "Unnamed item")[:200],
        "category": cat if cat in VALID_CATEGORIES else "other",
        "formality": form if form in VALID_FORMALITIES else "casual",
        "season": seas if seas in VALID_SEASONS else "all",
        "colors": [str(c)[:40] for c in cols][:5] if isinstance(cols, list) else [],
        "material": str(result.get("material") or "")[:100],
        "brand": str(result.get("brand") or "")[:100],
    }
    return True, cleaned


class AnalyzeClothingImageView(drf_views.APIView):
    """POST /api/wardrobe/analyze-image/  (multipart: image=<file>)

    Returns auto-detected clothing metadata from a photo. Does NOT persist
    anything — the client takes the returned fields, lets the user confirm/edit,
    and then POSTs them as a normal item create.
    """

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]
    serializer_class = None

    @extend_schema(
        summary="Analyze a clothing photo and auto-detect item fields",
        responses={
            200: inline_serializer(
                name="AnalyzeImageResponse",
                fields={
                    "name": serializers.CharField(),
                    "category": serializers.CharField(),
                    "formality": serializers.CharField(),
                    "season": serializers.CharField(),
                    "colors": serializers.ListField(child=serializers.CharField()),
                    "material": serializers.CharField(),
                    "brand": serializers.CharField(),
                },
            )
        },
    )
    def post(self, request):
        image = request.FILES.get("image")
        if not image:
            return Response(
                {"error": {"code": "missing_image", "message": "Upload an `image` file."}},
                status=400,
            )

        ok, payload = _analyze_clothing_image(image)
        if not ok:
            code = payload.get("error", {}).get("code")
            status_code = 503 if code == "not_configured" else 500
            return Response(payload, status=status_code)
        return Response(payload)


class ReceiptImportView(drf_views.APIView):
    serializer_class = None
    """
    POST /api/wardrobe/receipt-import/
    Body: { "email_body": "<raw email text>" }
    Parses a shopping receipt email (via Mistral) and returns ClothingItem
    candidates, optionally saving them when ``auto_save`` is set.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Import clothing items from receipt email",
        description="Parse a shopping receipt email body and create ClothingItem records.",
        responses={
            200: inline_serializer(
                name="ReceiptImportResponse",
                fields={
                    "status": serializers.CharField(),
                    "items_created": serializers.IntegerField(),
                },
            )
        },
    )
    def post(self, request):
        email_body = request.data.get("email_body", "")
        auto_save = request.data.get("auto_save", False)
        if not email_body:
            return Response({"detail": "email_body is required."}, status=400)

        from ritha.services.mistral_client import _has_mistral

        if not _has_mistral():
            return Response(
                {
                    "error": {
                        "code": "not_configured",
                        "message": "Receipt parsing requires MISTRAL_API_KEY in .env.",
                    },
                    "items": [],
                },
                status=503,
            )

        from ritha.services.mistral_client import chat_json

        prompt = (
            "Extract every clothing or fashion item from this shopping receipt / order confirmation email.\n"
            "For each item return a JSON object with these keys:\n"
            f'  - "name":      short descriptive name (e.g. "Navy cotton t-shirt")\n'
            f'  - "category":  one of {VALID_CATEGORIES}\n'
            f'  - "formality": one of {VALID_FORMALITIES}\n'
            f'  - "season":    one of {VALID_SEASONS} (use "all" if unsure)\n'
            '  - "colors":    list of 1-3 color names (lowercase)\n'
            '  - "material":  primary fabric if mentioned (e.g. "cotton", "denim"); empty string if unclear\n'
            '  - "brand":     brand name if mentioned; empty string otherwise\n'
            '  - "weight_grams": estimated weight in grams (integer); null if unknown\n'
            "\nIgnore non-clothing items (gift cards, shipping, tax, etc.).\n"
            f"\nReceipt text:\n{email_body[:4000]}\n"
            '\nReturn JSON: {"items": [...]}'
        )
        try:
            parsed = chat_json(prompt)
        except Exception as exc:
            logger.warning("Receipt parsing failed: %s", exc)
            return Response(
                {
                    "error": {
                        "code": "parse_failed",
                        "message": "Could not parse the receipt. Try a cleaner email body.",
                    },
                    "items": [],
                },
                status=500,
            )

        raw_items = parsed.get("items") or []
        cleaned = []
        for d in raw_items:
            cat = d.get("category")
            form = d.get("formality")
            seas = d.get("season")
            cols = d.get("colors")
            cleaned.append(
                {
                    "name": str(d.get("name") or "Unnamed item")[:200],
                    "category": cat if cat in VALID_CATEGORIES else "other",
                    "formality": form if form in VALID_FORMALITIES else "casual",
                    "season": seas if seas in VALID_SEASONS else "all",
                    "colors": [str(c)[:40] for c in cols][:5] if isinstance(cols, list) else [],
                    "material": str(d.get("material") or "")[:100],
                    "brand": str(d.get("brand") or "")[:100],
                    "weight_grams": d.get("weight_grams") if isinstance(d.get("weight_grams"), int) else None,
                }
            )

        if not auto_save:
            return Response({"status": "parsed", "items": cleaned})

        from .models import ClothingItem

        created = []
        for item_data in cleaned:
            wg = item_data.pop("weight_grams", None)
            item = ClothingItem.objects.create(user=request.user, **item_data)
            if wg is not None:
                item.weight_grams = wg
                item.save(update_fields=["weight_grams"])
            created.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "brand": item.brand,
                    "colors": item.colors,
                }
            )

        return Response({"status": "created", "items_created": len(created), "items": created})


class LuggageWeightView(drf_views.APIView):
    serializer_class = None
    """
    POST /api/wardrobe/luggage-weight/
    Body: { "item_ids": [1, 2, 3] }
    Returns estimated total weight and carry-on eligibility.
    """
    permission_classes = [permissions.IsAuthenticated]

    # IATA carry-on limits (kg) for common airlines
    AIRLINE_LIMITS = {
        "default": 10.0,
        "easyjet": 15.0,
        "ryanair": 10.0,
        "swiss": 10.0,
        "lufthansa": 8.0,
        "ba": 23.0,
    }
    # Average weights (grams) by category when item.weight_grams is null
    CATEGORY_DEFAULTS = {
        "top": 250,
        "bottom": 400,
        "outerwear": 800,
        "dress": 350,
        "footwear": 600,
        "accessory": 100,
        "activewear": 300,
        "formal": 700,
        "other": 300,
    }

    @extend_schema(
        summary="Calculate luggage weight and carry-on eligibility",
        description="Pass item_ids and optional airline. Returns weight, CO₂ saving, and carry-on tip.",
        responses={
            200: inline_serializer(
                name="LuggageWeightResponse",
                fields={
                    "total_grams": serializers.IntegerField(),
                    "total_kg": serializers.FloatField(),
                    "fits_carry_on": serializers.BooleanField(),
                    "co2_saved_vs_checked_kg": serializers.FloatField(),
                    "tip": serializers.CharField(),
                },
            )
        },
    )
    def post(self, request):
        item_ids = request.data.get("item_ids", [])
        airline = request.data.get("airline", "default").lower()

        from .models import ClothingItem

        items = ClothingItem.objects.filter(id__in=item_ids, user=request.user, is_active=True)

        if not items.exists():
            return Response({"detail": "No matching wardrobe items found."}, status=400)

        item_weights = []
        for item in items:
            weight = item.weight_grams or self.CATEGORY_DEFAULTS.get(item.category, 300)
            item_weights.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "weight_grams": weight,
                    "estimated": item.weight_grams is None,
                }
            )

        total_grams = sum(i["weight_grams"] for i in item_weights)
        total_kg = total_grams / 1000
        limit_kg = self.AIRLINE_LIMITS.get(airline, self.AIRLINE_LIMITS["default"])
        carries_on = total_kg <= limit_kg

        # CO2 saving estimate: every 10 kg of luggage ≈ 0.6 kg CO2 extra per flight hour
        # We give a simple "vs checked bag" comparison (checked avg = 20 kg)
        co2_vs_checked_kg = round(max(0, 20 - total_kg) * 0.03, 3)

        return Response(
            {
                "items": item_weights,
                "total_grams": total_grams,
                "total_kg": round(total_kg, 2),
                "airline": airline,
                "carry_on_limit_kg": limit_kg,
                "fits_carry_on": carries_on,
                "co2_saved_vs_checked_kg": co2_vs_checked_kg,
                "tip": (
                    "Great — carry-on only saves CO₂ and avoids baggage fees!"
                    if carries_on
                    else f"Over the {limit_kg} kg carry-on limit by {round(total_kg - limit_kg, 2)} kg. "
                    f"Consider removing {round((total_kg - limit_kg) * 1000)} g of items."
                ),
            }
        )


class BulkWardrobeUploadView(drf_views.APIView):
    """
    POST /api/wardrobe/bulk-upload/
    Upload multiple clothing items in one request.
    Body: {"items": [{name, category, formality, season, colors, material, brand}, ...]}
    Max 50 items per request.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None

    @extend_schema(
        summary="Bulk upload clothing items",
        description="Create up to 50 wardrobe items in one request.",
        responses={
            201: inline_serializer(
                name="BulkUploadResponse",
                fields={
                    "created": serializers.IntegerField(),
                    "errors": serializers.ListField(child=serializers.DictField()),
                },
            )
        },
    )
    def post(self, request):
        items_data = request.data.get("items", [])
        if not isinstance(items_data, list):
            return Response({"detail": "`items` must be a list."}, status=400)
        if len(items_data) > 50:
            return Response({"detail": "Maximum 50 items per request."}, status=400)
        if not items_data:
            return Response({"detail": "`items` list is empty."}, status=400)

        created, errors = [], []
        for idx, item_data in enumerate(items_data):
            ser = ClothingItemSerializer(data=item_data)
            if ser.is_valid():
                item = ser.save(user=request.user)
                created.append({"id": item.id, "name": item.name})
            else:
                errors.append({"index": idx, "errors": ser.errors})

        status_code = 201 if created else 400
        return Response(
            {"created": len(created), "items": created, "errors": errors},
            status=status_code,
        )


class WardrobePagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 100


@extend_schema_view(
    retrieve=extend_schema(parameters=[]),
    update=extend_schema(parameters=[]),
    partial_update=extend_schema(parameters=[]),
    destroy=extend_schema(parameters=[]),
)
class ClothingItemViewSet(viewsets.ModelViewSet):
    lookup_field = "pk"
    lookup_value_regex = r"[0-9]+"
    serializer_class = ClothingItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = WardrobePagination
    parser_classes = [parsers.MultiPartParser, parsers.JSONParser]

    def get_queryset(self):
        qs = ClothingItem.objects.filter(user=self.request.user, is_active=True).select_related("user")
        p = self.request.query_params

        category = p.get("category")
        formality = p.get("formality")
        season = p.get("season")
        q = p.get("q")  # free-text search on name, brand, material

        if category:
            qs = qs.filter(category=category)
        if formality:
            qs = qs.filter(formality=formality)
        if season:
            qs = qs.filter(season__in=[season, "all"])
        if q:
            from django.db.models import Q

            qs = qs.filter(Q(name__icontains=q) | Q(brand__icontains=q) | Q(material__icontains=q))
        return qs

    def perform_destroy(self, instance):
        """Soft-delete: set is_active=False instead of removing the row."""
        instance.is_active = False
        instance.save()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ── Starter pack ──────────────────────────────────────────────────────────────
@extend_schema(
    summary="Preview the starter pack for a (region, gender) combination",
    description=(
        "Returns the proposed wardrobe items for the user's demographic. Each "
        "item carries its prevalence percentage and survey citation so the "
        "client can render a tooltip explaining 'why is this here?'.\n\n"
        "If `region` or `gender` is omitted, falls back to the authenticated "
        "user's saved values. Region falls back to user.location-derived "
        "cluster lookup (TODO: geo-IP); for now, supply explicitly."
    ),
    parameters=[
        inline_serializer(
            name="StarterPackPreviewQuery",
            fields={
                "region": serializers.CharField(required=False, help_text="RegionCluster.code"),
                "gender": serializers.ChoiceField(required=False, choices=StarterPackItem.GENDER_CHOICES),
            },
        ),
    ],
    responses={200: StarterPackPreviewSerializer},
)
class StarterPackPreviewView(drf_views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        region_code = request.query_params.get("region") or _user_region_code(request.user)
        gender = request.query_params.get("gender") or request.user.gender

        if not region_code or not gender:
            return Response(
                {"error": "region and gender are required (either via query params or set on the user profile)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            region = RegionCluster.objects.get(code=region_code)
        except RegionCluster.DoesNotExist:
            return Response(
                {"error": f'unknown region "{region_code}"'},
                status=status.HTTP_404_NOT_FOUND,
            )

        items = StarterPackItem.objects.filter(
            region_cluster=region,
            gender=gender,
        ).order_by("sort_order", "-prevalence_pct")

        opt_in_groups = sorted(set(i.opt_in_group for i in items if i.is_opt_in and i.opt_in_group))

        data = StarterPackPreviewSerializer(
            {
                "region": region,
                "gender": gender,
                "items": items,
                "opt_in_groups": opt_in_groups,
            }
        ).data
        return Response(data)


@extend_schema(
    summary="Apply the starter pack to the user's wardrobe",
    description=(
        "Bulk-creates ClothingItem rows for every accepted StarterPackItem, "
        "plus any custom items the user typed in. Records the decision in "
        "StarterPackApplication for offline analysis (which items get rejected "
        "most often → demote them in the next pack version).\n\n"
        "Idempotent: if the user has already applied a starter pack, this "
        "returns 409 — call DELETE first if the user wants to redo onboarding."
    ),
    request=StarterPackApplyRequestSerializer,
    responses={
        201: StarterPackApplyResponseSerializer,
        409: inline_serializer(
            name="AlreadyApplied",
            fields={
                "error": serializers.CharField(),
                "application_id": serializers.IntegerField(),
            },
        ),
    },
)
class StarterPackApplyView(drf_views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = StarterPackApplyRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        user = request.user
        if hasattr(user, "starter_pack_application"):
            return Response(
                {
                    "error": "starter pack already applied for this user",
                    "application_id": user.starter_pack_application.id,
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            region = RegionCluster.objects.get(code=d["region_code"])
        except RegionCluster.DoesNotExist:
            return Response({"error": f'unknown region "{d["region_code"]}"'}, status=status.HTTP_404_NOT_FOUND)

        accepted = StarterPackItem.objects.filter(
            id__in=d["accepted_ids"],
            region_cluster=region,
            gender=d["gender"],
        )

        # Bulk-build ClothingItem rows
        items_to_create = []
        seed_targets = []  # (ClothingItem, subcategory) — for attaching cached region photos
        for sp in accepted:
            ci = ClothingItem(
                user=user,
                name=sp.display_name,
                category=sp.category,
                formality=sp.formality,
                season=sp.seasonality,
                colors=sp.default_colors,
                source="starter_pack",
                tags=[sp.subcategory],
            )
            items_to_create.append(ci)
            seed_targets.append((ci, sp.subcategory))

        # Custom items the user typed in (free-form)
        for c in d.get("custom_added", []):
            items_to_create.append(
                ClothingItem(
                    user=user,
                    name=c.get("name", "")[:200] or "Untitled",
                    category=c.get("category", "other"),
                    formality=c.get("formality", "casual"),
                    season=c.get("season", "all"),
                    colors=[],
                    source="manual",
                )
            )

        ClothingItem.objects.bulk_create(items_to_create)

        # Attach the cached region flat-lay photo to each created starter item, so a
        # freshly onboarded wardrobe shows real photos (falls back to the category
        # illustration in the UI when no image is cached). bulk_create populates PKs,
        # so image.save() updates the row in place.
        from wardrobe.images import attach_seed_image

        for ci, subcategory in seed_targets:
            if ci.pk:
                attach_seed_image(ci, region.code, d["gender"], subcategory)

        # Telemetry: which items were proposed, kept, rejected
        all_proposed = StarterPackItem.objects.filter(
            region_cluster=region,
            gender=d["gender"],
            is_default=True,
        ).values_list("id", "subcategory")
        accepted_ids = set(d["accepted_ids"])
        proposed_log = [{"id": pid, "subcategory": sub, "was_kept": pid in accepted_ids} for pid, sub in all_proposed]

        app = StarterPackApplication.objects.create(
            user=user,
            region_cluster=region,
            gender=d["gender"],
            proposed_items=proposed_log,
            custom_added=d.get("custom_added", []),
            opt_ins=d.get("opt_ins", []),
            pack_version=1,
        )

        return Response(
            {"items_created": len(items_to_create), "application_id": app.id},
            status=status.HTTP_201_CREATED,
        )


# Timezone-prefix → region cluster heuristic. Cheap, no network, no geo-IP.
# Order matters: more-specific prefixes first (Asia/Kolkata before Asia/).
# Latin America is special-cased before America/ catches everything as NA.
_TZ_REGION_MAP = [
    # South Asia
    ("Asia/Kolkata", "south_asian_tropical"),
    ("Asia/Dhaka", "south_asian_tropical"),
    ("Asia/Colombo", "south_asian_tropical"),
    ("Asia/Karachi", "south_asian_tropical"),
    ("Asia/Kathmandu", "south_asian_tropical"),
    # MENA
    ("Asia/Riyadh", "mena_arid"),
    ("Asia/Dubai", "mena_arid"),
    ("Asia/Qatar", "mena_arid"),
    ("Asia/Kuwait", "mena_arid"),
    ("Asia/Bahrain", "mena_arid"),
    ("Asia/Muscat", "mena_arid"),
    ("Asia/Amman", "mena_arid"),
    ("Asia/Beirut", "mena_arid"),
    ("Africa/Cairo", "mena_arid"),
    ("Africa/Casablanca", "mena_arid"),
    ("Africa/Tunis", "mena_arid"),
    ("Africa/Algiers", "mena_arid"),
    ("Africa/Tripoli", "mena_arid"),
    # East / SE Asia subtropical
    ("Asia/Bangkok", "east_asian_subtropical"),
    ("Asia/Ho_Chi_Minh", "east_asian_subtropical"),
    ("Asia/Manila", "east_asian_subtropical"),
    ("Asia/Kuala_Lumpur", "east_asian_subtropical"),
    ("Asia/Singapore", "east_asian_subtropical"),
    ("Asia/Jakarta", "east_asian_subtropical"),
    ("Asia/Hong_Kong", "east_asian_subtropical"),
    ("Asia/Phnom_Penh", "east_asian_subtropical"),
    ("Asia/Vientiane", "east_asian_subtropical"),
    ("Asia/Brunei", "east_asian_subtropical"),
    # Latin America (must come before America/ catch-all)
    ("America/Sao_Paulo", "latam_tropical"),
    ("America/Recife", "latam_tropical"),
    ("America/Bahia", "latam_tropical"),
    ("America/Fortaleza", "latam_tropical"),
    ("America/Manaus", "latam_tropical"),
    ("America/Mexico_City", "latam_tropical"),
    ("America/Cancun", "latam_tropical"),
    ("America/Bogota", "latam_tropical"),
    ("America/Caracas", "latam_tropical"),
    ("America/Costa_Rica", "latam_tropical"),
    ("America/Panama", "latam_tropical"),
    ("America/Havana", "latam_tropical"),
    ("America/Santo_Domingo", "latam_tropical"),
    ("America/Tegucigalpa", "latam_tropical"),
    ("America/Managua", "latam_tropical"),
    ("America/El_Salvador", "latam_tropical"),
    ("America/Guatemala", "latam_tropical"),
    # North America
    ("America/", "na_temperate"),
    ("US/", "na_temperate"),
    ("Canada/", "na_temperate"),
    # NW Europe
    ("Europe/", "nw_temperate"),
    ("GB", "nw_temperate"),
    ("UTC", "nw_temperate"),
]


def _region_from_timezone(tz: str | None) -> str | None:
    if not tz:
        return None
    for prefix, region in _TZ_REGION_MAP:
        if tz == prefix or tz.startswith(prefix):
            return region
    return None


def _user_region_code(user) -> str | None:
    """Best-effort region lookup, in priority order:
       1. Explicit override in user.style_profile.region_cluster
       2. Timezone-prefix heuristic (cheap; no extra fields needed)
       3. None — caller surfaces region picker.
    Phase 2: refine via user.location_lat/lon → Köppen + cultural cluster."""
    if hasattr(user, "style_profile") and isinstance(user.style_profile, dict):
        explicit = user.style_profile.get("region_cluster")
        if explicit:
            return explicit
    return _region_from_timezone(getattr(user, "timezone", None))


# ── Region listing ────────────────────────────────────────────────────────────


@extend_schema(
    summary="List all available region clusters",
    description=(
        "Returns the catalogue of region buckets the starter-pack system "
        "supports (Phase 1: 3 regions). Clients should call this on first run "
        "instead of hardcoding the list — new regions added server-side become "
        "available without a client update.\n\n"
        "Includes `suggested_region`, the server's best guess for the current "
        "user based on their timezone, so clients can pre-select."
    ),
    responses={
        200: inline_serializer(
            name="RegionListResponse",
            fields={
                "regions": RegionClusterSerializer(many=True),
                "suggested_region": serializers.CharField(allow_null=True),
            },
        )
    },
)
class RegionListView(drf_views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        regions = RegionCluster.objects.all().order_by("display_name")
        return Response(
            {
                "regions": RegionClusterSerializer(regions, many=True).data,
                "suggested_region": _user_region_code(request.user),
            }
        )
