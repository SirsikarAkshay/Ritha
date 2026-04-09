import logging

from rest_framework import viewsets, parsers, permissions, views as drf_views
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer
from rest_framework import serializers
from .models import ClothingItem
from .serializers import ClothingItemSerializer

logger = logging.getLogger(__name__)


VALID_CATEGORIES = ['top', 'bottom', 'dress', 'outerwear', 'footwear',
                    'accessory', 'activewear', 'formal', 'other']
VALID_FORMALITIES = ['casual', 'casual_smart', 'smart', 'formal', 'activewear']
VALID_SEASONS     = ['spring', 'summer', 'autumn', 'winter', 'all']

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
    from arokah.services.mistral_client import _has_mistral, chat_image_json

    if not _has_mistral():
        return False, {
            'error': {
                'code': 'not_configured',
                'message': 'Image analysis is unavailable. MISTRAL_API_KEY is not set.',
            },
        }

    try:
        image_file.seek(0)
    except Exception:
        pass
    image_bytes = image_file.read()
    mime_type = getattr(image_file, 'content_type', None) or 'image/jpeg'

    try:
        result = chat_image_json(ANALYZE_PROMPT, image_bytes, mime_type)
    except Exception as exc:
        logger.warning('Clothing image analysis failed: %s', exc)
        return False, {
            'error': {
                'code': 'analysis_failed',
                'message': 'Could not analyze the image. Please try a clearer photo.',
            },
        }

    cat  = result.get('category')
    form = result.get('formality')
    seas = result.get('season')
    cols = result.get('colors')

    cleaned = {
        'name':      str(result.get('name') or 'Unnamed item')[:200],
        'category':  cat  if cat  in VALID_CATEGORIES  else 'other',
        'formality': form if form in VALID_FORMALITIES else 'casual',
        'season':    seas if seas in VALID_SEASONS     else 'all',
        'colors':    [str(c)[:40] for c in cols][:5] if isinstance(cols, list) else [],
        'material':  str(result.get('material') or '')[:100],
        'brand':     str(result.get('brand') or '')[:100],
    }
    return True, cleaned


class AnalyzeClothingImageView(drf_views.APIView):
    """POST /api/wardrobe/analyze-image/  (multipart: image=<file>)

    Returns auto-detected clothing metadata from a photo. Does NOT persist
    anything — the client takes the returned fields, lets the user confirm/edit,
    and then POSTs them as a normal item create.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes     = [MultiPartParser]
    serializer_class   = None

    @extend_schema(
        summary="Analyze a clothing photo and auto-detect item fields",
        responses={200: inline_serializer(name='AnalyzeImageResponse', fields={
            'name':      serializers.CharField(),
            'category':  serializers.CharField(),
            'formality': serializers.CharField(),
            'season':    serializers.CharField(),
            'colors':    serializers.ListField(child=serializers.CharField()),
            'material':  serializers.CharField(),
            'brand':     serializers.CharField(),
        })},
    )
    def post(self, request):
        image = request.FILES.get('image')
        if not image:
            return Response(
                {'error': {'code': 'missing_image', 'message': 'Upload an `image` file.'}},
                status=400,
            )

        ok, payload = _analyze_clothing_image(image)
        if not ok:
            code = payload.get('error', {}).get('code')
            status_code = 503 if code == 'not_configured' else 500
            return Response(payload, status=status_code)
        return Response(payload)


class BackgroundRemovalView(drf_views.APIView):
    serializer_class = None
    """
    POST /api/wardrobe/background-removal/
    Upload an image; returns a URL to the cleaned (background-removed) version.
    Currently a stub — wire up Google Vision / Remove.bg in production.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes     = [MultiPartParser]

    @extend_schema(
        summary="Remove background from clothing photo",
        description="Upload a garment image; returns URL to background-removed version.",
        responses={200: inline_serializer(name='BgRemovalResponse', fields={
            'status': serializers.CharField(),
            'message': serializers.CharField(),
            'original_filename': serializers.CharField(),
        })},
    )
    def post(self, request):
        image = request.FILES.get('image')
        if not image:
            return Response({'detail': 'No image file provided.'}, status=400)
        return Response({
            'status':  'stub',
            'message': 'Background removal not yet connected. Upload the item normally and the cleaned image will be generated asynchronously.',
            'original_filename': image.name,
        })


class ReceiptImportView(drf_views.APIView):
    serializer_class = None
    """
    POST /api/wardrobe/receipt-import/
    Body: { "email_body": "<raw email text>" }
    Parses a shopping receipt email and creates ClothingItem records.
    Currently a stub — wire up OpenAI parsing in production.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Import clothing items from receipt email",
        description="Parse a shopping receipt email body and create ClothingItem records.",
        responses={200: inline_serializer(name='ReceiptImportResponse', fields={
            'status': serializers.CharField(),
            'items_created': serializers.IntegerField(),
        })},
    )
    def post(self, request):
        email_body = request.data.get('email_body', '')
        if not email_body:
            return Response({'detail': 'email_body is required.'}, status=400)

        from django.conf import settings
        from arokah.services.mistral_client import _has_mistral
        if not _has_mistral():
            return Response({
                'status':  'stub',
                'message': 'Receipt parsing requires OpenAI. Add your API key to .env to activate.',
                'items_created': 0,
            })

        # Live path: call Mistral to extract item names/categories from receipt text
        from arokah.services.mistral_client import chat_json
        prompt = f"""Extract clothing items from this shopping receipt email.
For each item return: name, category (top/bottom/outerwear/footwear/accessory/activewear/other),
colors (list), brand (if mentioned), material (if mentioned).

Receipt:
{email_body[:3000]}

Return JSON: {{"items": [{{"name":"...","category":"...","colors":[],"brand":"","material":""}}]}}"""
        parsed = chat_json(prompt)
        created = []
        from .models import ClothingItem
        for item_data in parsed.get('items', []):
            item = ClothingItem.objects.create(
                user=request.user,
                name=item_data.get('name', 'Unnamed item'),
                category=item_data.get('category', 'other'),
                colors=item_data.get('colors', []),
                brand=item_data.get('brand', ''),
                material=item_data.get('material', ''),
            )
            created.append({'id': item.id, 'name': item.name})

        return Response({'status': 'success', 'items_created': len(created), 'items': created})


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
        'default':  10.0,
        'easyjet':  15.0,
        'ryanair':  10.0,
        'swiss':    10.0,
        'lufthansa': 8.0,
        'ba':       23.0,
    }
    # Average weights (grams) by category when item.weight_grams is null
    CATEGORY_DEFAULTS = {
        'top':        250,
        'bottom':     400,
        'outerwear':  800,
        'dress':      350,
        'footwear':   600,
        'accessory':  100,
        'activewear': 300,
        'formal':     700,
        'other':      300,
    }

    @extend_schema(
        summary="Calculate luggage weight and carry-on eligibility",
        description="Pass item_ids and optional airline. Returns weight, CO₂ saving, and carry-on tip.",
        responses={200: inline_serializer(name='LuggageWeightResponse', fields={
            'total_grams': serializers.IntegerField(),
            'total_kg': serializers.FloatField(),
            'fits_carry_on': serializers.BooleanField(),
            'co2_saved_vs_checked_kg': serializers.FloatField(),
            'tip': serializers.CharField(),
        })},
    )
    def post(self, request):
        item_ids = request.data.get('item_ids', [])
        airline  = request.data.get('airline', 'default').lower()

        from .models import ClothingItem
        items = ClothingItem.objects.filter(id__in=item_ids, user=request.user, is_active=True)

        if not items.exists():
            return Response({'detail': 'No matching wardrobe items found.'}, status=400)

        item_weights = []
        for item in items:
            weight = item.weight_grams or self.CATEGORY_DEFAULTS.get(item.category, 300)
            item_weights.append({'id': item.id, 'name': item.name,
                                 'category': item.category, 'weight_grams': weight,
                                 'estimated': item.weight_grams is None})

        total_grams = sum(i['weight_grams'] for i in item_weights)
        total_kg    = total_grams / 1000
        limit_kg    = self.AIRLINE_LIMITS.get(airline, self.AIRLINE_LIMITS['default'])
        carries_on  = total_kg <= limit_kg

        # CO2 saving estimate: every 10 kg of luggage ≈ 0.6 kg CO2 extra per flight hour
        # We give a simple "vs checked bag" comparison (checked avg = 20 kg)
        co2_vs_checked_kg = round(max(0, 20 - total_kg) * 0.03, 3)

        return Response({
            'items':                   item_weights,
            'total_grams':             total_grams,
            'total_kg':                round(total_kg, 2),
            'airline':                 airline,
            'carry_on_limit_kg':       limit_kg,
            'fits_carry_on':           carries_on,
            'co2_saved_vs_checked_kg': co2_vs_checked_kg,
            'tip': (
                'Great — carry-on only saves CO₂ and avoids baggage fees!' if carries_on
                else f'Over the {limit_kg} kg carry-on limit by {round(total_kg - limit_kg, 2)} kg. '
                     f'Consider removing {round((total_kg - limit_kg) * 1000)} g of items.'
            ),
        })




class BulkWardrobeUploadView(drf_views.APIView):
    """
    POST /api/wardrobe/bulk-upload/
    Upload multiple clothing items in one request.
    Body: {"items": [{name, category, formality, season, colors, material, brand}, ...]}
    Max 50 items per request.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    @extend_schema(
        summary="Bulk upload clothing items",
        description="Create up to 50 wardrobe items in one request.",
        responses={201: inline_serializer(name='BulkUploadResponse', fields={
            'created': serializers.IntegerField(),
            'errors':  serializers.ListField(child=serializers.DictField()),
        })},
    )
    def post(self, request):
        items_data = request.data.get('items', [])
        if not isinstance(items_data, list):
            return Response({'detail': '`items` must be a list.'}, status=400)
        if len(items_data) > 50:
            return Response({'detail': 'Maximum 50 items per request.'}, status=400)
        if not items_data:
            return Response({'detail': '`items` list is empty.'}, status=400)

        created, errors = [], []
        for idx, item_data in enumerate(items_data):
            ser = ClothingItemSerializer(data=item_data)
            if ser.is_valid():
                item = ser.save(user=request.user)
                created.append({'id': item.id, 'name': item.name})
            else:
                errors.append({'index': idx, 'errors': ser.errors})

        status_code = 201 if created else 400
        return Response(
            {'created': len(created), 'items': created, 'errors': errors},
            status=status_code,
        )


class WardrobePagination(PageNumberPagination):
    page_size             = 24
    page_size_query_param = 'page_size'
    max_page_size         = 100


@extend_schema_view(
    retrieve=extend_schema(parameters=[]),
    update=extend_schema(parameters=[]),
    partial_update=extend_schema(parameters=[]),
    destroy=extend_schema(parameters=[]),
)
class ClothingItemViewSet(viewsets.ModelViewSet):
    lookup_field = "pk"
    lookup_value_regex = r"[0-9]+"
    serializer_class   = ClothingItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class   = WardrobePagination
    parser_classes     = [parsers.MultiPartParser, parsers.JSONParser]

    def get_queryset(self):
        qs = ClothingItem.objects.filter(user=self.request.user, is_active=True).select_related('user')
        p  = self.request.query_params

        category = p.get('category')
        formality = p.get('formality')
        season    = p.get('season')
        q         = p.get('q')   # free-text search on name, brand, material

        if category:
            qs = qs.filter(category=category)
        if formality:
            qs = qs.filter(formality=formality)
        if season:
            qs = qs.filter(season__in=[season, 'all'])
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(brand__icontains=q) |
                Q(material__icontains=q)
            )
        return qs

    def perform_destroy(self, instance):
        """Soft-delete: set is_active=False instead of removing the row."""
        instance.is_active = False
        instance.save()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
