from rest_framework import serializers
from .models import ChatThread, Message
from UserData.serializers import SimpleUserSerializer  # you already have this

class MessageSerializer(serializers.ModelSerializer):
    sender = SimpleUserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "thread", "sender", "text", "created_at", "is_read"]
        read_only_fields = ["id", "created_at", "is_read", "sender", "thread"]


class ChatThreadSerializer(serializers.ModelSerializer):
    user1 = serializers.SerializerMethodField()
    user2 = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = ["id", "user1", "user2", "created_at", "last_message"]

    def get_user1(self, obj):
        return SimpleUserSerializer(obj.user_low).data

    def get_user2(self, obj):
        return SimpleUserSerializer(obj.user_high).data

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        return MessageSerializer(msg).data if msg else None
