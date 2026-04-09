from django.urls import path

from .views import (
    ConversationListView,
    ConversationOpenView,
    MessageListView,
    SendMessageView,
    MarkReadView,
)

urlpatterns = [
    path('conversations/',                ConversationListView.as_view()),
    path('conversations/open/',           ConversationOpenView.as_view()),
    path('conversations/<int:pk>/messages/',  MessageListView.as_view()),
    path('conversations/<int:pk>/send/',      SendMessageView.as_view()),
    path('conversations/<int:pk>/mark_read/', MarkReadView.as_view()),
]
