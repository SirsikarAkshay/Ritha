from django.urls import path

from .views import (
    InvitationListView,
    InvitationRespondView,
    ItemDetailView,
    ItemListCreateView,
    MemberAddView,
    MemberRemoveView,
    WardrobeDetailView,
    WardrobeListCreateView,
)

urlpatterns = [
    path("", WardrobeListCreateView.as_view()),
    path("invitations/", InvitationListView.as_view()),
    path("invitations/<int:pk>/respond/", InvitationRespondView.as_view()),
    path("<int:pk>/", WardrobeDetailView.as_view()),
    path("<int:pk>/members/", MemberAddView.as_view()),
    path("<int:pk>/members/<int:user_id>/", MemberRemoveView.as_view()),
    path("<int:pk>/items/", ItemListCreateView.as_view()),
    path("<int:pk>/items/<int:item_id>/", ItemDetailView.as_view()),
]
