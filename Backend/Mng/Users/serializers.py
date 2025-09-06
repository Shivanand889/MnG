from rest_framework import serializers
from .models import *
from UserData.models import Connection, ConnectionRequest

# Register / Create User Serializer
class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Users
        fields = ['id', 'email', 'username', 'password']
        read_only_fields = ['id']

    def create(self, validated_data):
        user = Users.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user


# General User Info Serializer (e.g., profile view)
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = [
            'id', 'email', 'username', 'is_active',
            'created_at', 'last_login'
        ]
        read_only_fields = ['id', 'created_at', 'last_login']



from rest_framework import serializers
from .models import Interest

class AddInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interest
        fields = ['name']

    # Allow bulk creation
    def create(self, validated_data):
        if isinstance(validated_data['name'], list):
            interests = [Interest(name=name) for name in validated_data['name']]
            Interest.objects.bulk_create(interests)
            return interests
        else:
            return super().create(validated_data)


# User Profile Serializer
class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interest
        fields = ['id', 'name']


# Serializer for UserProfile model
class UserProfileSerializer(serializers.ModelSerializer):
    # Nested representation for interests
    interests = InterestSerializer(many=True, read_only=True)
    # To allow adding interest IDs when creating/updating profile
    interest_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Interest.objects.all(), write_only=True, source='interests'
    )

    class Meta:
        model = UserProfile
        fields = [
            'id',
            'user',
            'full_name',
            'gender',
            'birthdate',
            'bio',
            'job_title',
            'company',
            'education',
            'interests',      # read-only nested interests
            'interest_ids',   # write-only for assigning interests
            'is_premium',
            'premium_since',
        ]
        read_only_fields = ['id', 'user']


# Profile Photo Serializer
class ProfilePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfilePhoto
        fields = [
            'id', 'user', 'url', 'position',
            'uploaded_at', 'is_private'
        ]
        read_only_fields = ['id', 'uploaded_at']

class UserListSerializer(serializers.ModelSerializer):
    thread_id = serializers.SerializerMethodField()
    connection_status = serializers.SerializerMethodField()

    class Meta:
        model = Users
        fields = ["id", "username", "email", "thread_id", "connection_status"]

    def get_thread_id(self, obj):
        current_user = self.context.get("current_user")
        if not current_user:
            return None

        from Chat.models import ChatThread
        low, high = (current_user, obj) if current_user.id < obj.id else (obj, current_user)
        thread = ChatThread.objects.filter(user_low=low, user_high=high).first()
        return thread.id if thread else None

    def get_connection_status(self, obj):
        current_user = self.context.get("current_user")
        if not current_user:
            return "none"


        if Connection.objects.filter(user=current_user, connected_user=obj).exists():
            return "connected"
        elif ConnectionRequest.objects.filter(from_user=current_user, to_user=obj, status="pending").exists():
            return "pending"
        elif ConnectionRequest.objects.filter(from_user=obj, to_user=current_user, status="pending").exists():
            return "incoming"
        else:
            return "none"


class SimpleUserSerializer(serializers.ModelSerializer):
    """Simple serializer for basic user info used in other serializers"""
    class Meta:
        model = Users
        fields = ['id', 'username', 'email']
        read_only_fields = ['id', 'username', 'email']
