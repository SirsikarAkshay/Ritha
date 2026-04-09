from django.urls import path

from .views import (
    WardrobeListCreateView,
    WardrobeDetailView,
    MemberAddView,
    MemberRemoveView,
    ItemListCreateView,
    ItemDeleteView,
)

urlpatterns = [
    path('',                                    WardrobeListCreateView.as_view()),
    path('<int:pk>/',                           WardrobeDetailView.as_view()),
    path('<int:pk>/members/',                   MemberAddView.as_view()),
    path('<int:pk>/members/<int:user_id>/',     MemberRemoveView.as_view()),
    path('<int:pk>/items/',                     ItemListCreateView.as_view()),
    path('<int:pk>/items/<int:item_id>/',       ItemDeleteView.as_view()),
]
