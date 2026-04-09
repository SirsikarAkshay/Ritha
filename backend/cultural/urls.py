from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CulturalRuleViewSet, LocalEventViewSet

router = DefaultRouter()
router.register('rules',  CulturalRuleViewSet,  basename='cultural-rule')
router.register('events', LocalEventViewSet,     basename='local-event')

urlpatterns = [path('', include(router.urls))]
