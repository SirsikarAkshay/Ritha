from django.urls import path

from .views import (
    BlockListView,
    ConnectionAcceptView,
    ConnectionDeleteView,
    ConnectionListView,
    ConnectionRejectView,
    ConnectionRequestView,
    MyProfileView,
    UnblockView,
    UpdateHandleView,
    UserSearchView,
)

urlpatterns = [
    # Profile
    path('me/profile/',                 MyProfileView.as_view(),       name='social-my-profile'),
    path('me/profile/handle/',          UpdateHandleView.as_view(),    name='social-update-handle'),

    # Discovery
    path('users/search/',               UserSearchView.as_view(),      name='social-user-search'),

    # Connections
    path('connections/',                ConnectionListView.as_view(),  name='social-connection-list'),
    path('connections/request/',        ConnectionRequestView.as_view(), name='social-connection-request'),
    path('connections/<int:pk>/',       ConnectionDeleteView.as_view(), name='social-connection-delete'),
    path('connections/<int:pk>/accept/', ConnectionAcceptView.as_view(), name='social-connection-accept'),
    path('connections/<int:pk>/reject/', ConnectionRejectView.as_view(), name='social-connection-reject'),

    # Blocks
    path('blocks/',                     BlockListView.as_view(),       name='social-block-list'),
    path('blocks/<int:pk>/',            UnblockView.as_view(),         name='social-unblock'),
]
