from rest_framework import serializers

from social.serializers import PublicUserSerializer
from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Message
        fields = ['id', 'conversation', 'sender', 'body', 'created_at']
        read_only_fields = ['id', 'conversation', 'sender', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    other_user    = serializers.SerializerMethodField()
    last_message  = serializers.SerializerMethodField()
    unread_count  = serializers.SerializerMethodField()

    class Meta:
        model  = Conversation
        fields = ['id', 'other_user', 'last_message', 'unread_count', 'updated_at']

    def _me(self):
        return self.context['request'].user

    def get_other_user(self, obj):
        other = obj.other_user(self._me())
        return PublicUserSerializer(other, context=self.context).data

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        return MessageSerializer(msg).data if msg else None

    def get_unread_count(self, obj):
        return obj.unread_count_for(self._me())
