from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OutfitRecommendationViewSet, OutfitHistoryView

router = DefaultRouter()
router.register('recommendations', OutfitRecommendationViewSet, basename='outfit')

urlpatterns = [
    path('', include(router.urls)),
    path('history/', OutfitHistoryView.as_view(), name='outfit-history'),
]
