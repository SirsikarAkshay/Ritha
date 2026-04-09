from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AnalyzeClothingImageView,
    BackgroundRemovalView,
    BulkWardrobeUploadView,
    ClothingItemViewSet,
    LuggageWeightView,
    ReceiptImportView,
)

router = DefaultRouter()
router.register('items', ClothingItemViewSet, basename='clothing-item')

urlpatterns = [
    path('', include(router.urls)),
    path('analyze-image/',      AnalyzeClothingImageView.as_view(), name='analyze-image'),
    path('background-removal/', BackgroundRemovalView.as_view(), name='background-removal'),
    path('receipt-import/',     ReceiptImportView.as_view(),     name='receipt-import'),
    path('luggage-weight/',     LuggageWeightView.as_view(),     name='luggage-weight'),
    path('bulk-upload/',        BulkWardrobeUploadView.as_view(),  name='bulk-upload'),
]
