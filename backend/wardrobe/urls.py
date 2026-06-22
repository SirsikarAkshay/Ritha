from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AnalyzeClothingImageView,
    BulkWardrobeUploadView,
    ClothingItemViewSet,
    LuggageWeightView,
    ReceiptImportView,
    RegionListView,
    StarterPackApplyView,
    StarterPackPreviewView,
)

router = DefaultRouter()
router.register("items", ClothingItemViewSet, basename="clothing-item")

urlpatterns = [
    path("", include(router.urls)),
    path("analyze-image/", AnalyzeClothingImageView.as_view(), name="analyze-image"),
    path("receipt-import/", ReceiptImportView.as_view(), name="receipt-import"),
    path("luggage-weight/", LuggageWeightView.as_view(), name="luggage-weight"),
    path("bulk-upload/", BulkWardrobeUploadView.as_view(), name="bulk-upload"),
    path("starter-pack/regions/", RegionListView.as_view(), name="starter-pack-regions"),
    path("starter-pack/preview/", StarterPackPreviewView.as_view(), name="starter-pack-preview"),
    path("starter-pack/apply/", StarterPackApplyView.as_view(), name="starter-pack-apply"),
]
