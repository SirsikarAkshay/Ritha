from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SustainabilityLogViewSet, SustainabilityTrackerView

router = DefaultRouter()
router.register('logs', SustainabilityLogViewSet, basename='sustainability-log')

urlpatterns = [
    path('', include(router.urls)),
    path('tracker/', SustainabilityTrackerView.as_view(), name='sustainability-tracker'),
]
