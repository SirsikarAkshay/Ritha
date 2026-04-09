from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CalendarEventViewSet, TripViewSet, PackingChecklistViewSet

router = DefaultRouter()
router.register('events', CalendarEventViewSet, basename='event')
router.register('trips',     TripViewSet,              basename='trip')
router.register('checklist', PackingChecklistViewSet, basename='checklist')

urlpatterns = [path('', include(router.urls))]
