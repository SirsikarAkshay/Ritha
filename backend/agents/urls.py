from django.urls import path
from .views import (
    DailyLookView, PackingListView, OutfitPlannerView,
    CulturalAdvisorView, ConflictDetectorView, SmartRecommendView,
)

urlpatterns = [
    path('daily-look/',        DailyLookView.as_view(),        name='agent-daily-look'),
    path('packing-list/',      PackingListView.as_view(),      name='agent-packing-list'),
    path('outfit-planner/',    OutfitPlannerView.as_view(),     name='agent-outfit-planner'),
    path('cultural-advisor/',  CulturalAdvisorView.as_view(),  name='agent-cultural-advisor'),
    path('conflict-detector/', ConflictDetectorView.as_view(), name='agent-conflict-detector'),
    path('smart-recommend/',   SmartRecommendView.as_view(),   name='agent-smart-recommend'),
]
