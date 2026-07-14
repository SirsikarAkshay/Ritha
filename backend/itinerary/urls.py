from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CalendarEventViewSet,
    PackingChecklistViewSet,
    SavedShoppingItemViewSet,
    TripViewSet,
)

router = DefaultRouter()
router.register("events", CalendarEventViewSet, basename="event")
router.register("trips", TripViewSet, basename="trip")
router.register("checklist", PackingChecklistViewSet, basename="checklist")
router.register("shopping-list", SavedShoppingItemViewSet, basename="shopping-list")

urlpatterns = [path("", include(router.urls))]
