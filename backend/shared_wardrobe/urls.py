from django.urls import path

from .views import (
    InvitationListView,
    InvitationRespondView,
    ItemClaimView,
    ItemDetailView,
    ItemListCreateView,
    MemberAddView,
    MemberRemoveView,
    WardrobeDetailView,
    WardrobeInviteLinkView,
    WardrobeJoinView,
    WardrobeListCreateView,
)

urlpatterns = [
    path("", WardrobeListCreateView.as_view()),
    path("join/", WardrobeJoinView.as_view()),
    path("invitations/", InvitationListView.as_view()),
    path("invitations/<int:pk>/respond/", InvitationRespondView.as_view()),
    path("<int:pk>/", WardrobeDetailView.as_view()),
    path("<int:pk>/invite-link/", WardrobeInviteLinkView.as_view()),
    path("<int:pk>/members/", MemberAddView.as_view()),
    path("<int:pk>/members/<int:user_id>/", MemberRemoveView.as_view()),
    path("<int:pk>/items/", ItemListCreateView.as_view()),
    path("<int:pk>/items/<int:item_id>/", ItemDetailView.as_view()),
    path("<int:pk>/items/<int:item_id>/claim/", ItemClaimView.as_view()),
]
