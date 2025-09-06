from rest_framework import serializers
from .models import *


# Show minimal user info inside requests/connections
class SimpleUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="profile.full_name", read_only=True)
    photo = serializers.SerializerMethodField()

    class Meta:
        model = Users
        fields = ["id", "username", "full_name", "photo"]

    def get_photo(self, obj):
        photo = obj.photos.filter(is_private=False).first()
        return photo.url if photo else None


# Serializer for Connection model
class ConnectionSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)
    connected_user = SimpleUserSerializer(read_only=True)

    class Meta:
        model = Connection
        fields = ["id", "user", "connected_user", "created_at"]


# Serializer for ConnectionRequest model
class ConnectionRequestSerializer(serializers.ModelSerializer):
    from_user = SimpleUserSerializer(read_only=True)
    to_user = SimpleUserSerializer(read_only=True)

    class Meta:
        model = ConnectionRequest
        fields = ["id", "from_user", "to_user", "status", "created_at", "updated_at"]
