from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OutfitHistoryView, OutfitPreferencesView, OutfitRecommendationViewSet

router = DefaultRouter()
router.register("recommendations", OutfitRecommendationViewSet, basename="outfit")

urlpatterns = [
    path("", include(router.urls)),
    path("history/", OutfitHistoryView.as_view(), name="outfit-history"),
    path("preferences/", OutfitPreferencesView.as_view(), name="outfit-preferences"),
]
