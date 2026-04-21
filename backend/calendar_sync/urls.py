from django.urls import path
from .views import (
    CalendarStatusView,
    GoogleWebhookView,
    GoogleConnectView, GoogleCallbackView, GoogleSyncView, GoogleDisconnectView,
    AppleConnectView, AppleSyncView, AppleDisconnectView,
    OutlookConnectView, OutlookCallbackView, OutlookSyncView, OutlookDisconnectView,
    DeviceCalendarSyncView,
)

urlpatterns = [
    path('status/',                   CalendarStatusView.as_view(),    name='calendar-status'),
    path('device/sync/',              DeviceCalendarSyncView.as_view(), name='device-calendar-sync'),
    path('google/connect/',           GoogleConnectView.as_view(),     name='google-connect'),
    path('google/callback/',          GoogleCallbackView.as_view(),    name='google-callback'),
    path('google/sync/',              GoogleSyncView.as_view(),        name='google-sync'),
    path('google/disconnect/',        GoogleDisconnectView.as_view(),  name='google-disconnect'),
    path('apple/connect/',            AppleConnectView.as_view(),      name='apple-connect'),
    path('apple/sync/',               AppleSyncView.as_view(),         name='apple-sync'),
    path('apple/disconnect/',         AppleDisconnectView.as_view(),   name='apple-disconnect'),
    path('outlook/connect/',          OutlookConnectView.as_view(),    name='outlook-connect'),
    path('outlook/callback/',         OutlookCallbackView.as_view(),   name='outlook-callback'),
    path('outlook/sync/',             OutlookSyncView.as_view(),       name='outlook-sync'),
    path('outlook/disconnect/',       OutlookDisconnectView.as_view(), name='outlook-disconnect'),
    path('google/webhook/',           GoogleWebhookView.as_view(),     name='google-webhook'),
]
