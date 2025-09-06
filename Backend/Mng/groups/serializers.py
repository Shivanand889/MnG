# groups/serializers.py - Fixed version

from rest_framework import serializers
from .models import Group, GroupMember, GroupMessage, GroupJoinRequest
from Users.models import Interest
from Users.serializers import InterestSerializer, SimpleUserSerializer

class GroupSerializer(serializers.ModelSerializer):
    interests = InterestSerializer(many=True, read_only=True)
    interest_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Interest.objects.all(), write_only=True, source='interests'
    )
    created_by = SimpleUserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 'interests', 'interest_ids',
            'created_by', 'created_at', 'member_count', 'is_member', 'user_role'
        ]
        read_only_fields = ['id', 'created_by', 'created_at']
    
    def get_member_count(self, obj):
        return obj.members.count()
    
    def get_is_member(self, obj):
        user = self.context.get('current_user')
        if not user:
            return False
        return obj.members.filter(user=user).exists()
    
    def get_user_role(self, obj):
        user = self.context.get('current_user')
        if not user:
            return None
        member = obj.members.filter(user=user).first()
        return member.role if member else None


class CreateGroupSerializer(serializers.ModelSerializer):
    interest_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Interest.objects.all(), source='interests', required=False
    )
    
    class Meta:
        model = Group
        fields = ['name', 'description', 'interest_ids']
    
    def create(self, validated_data):
        user = self.context['request'].user
        interests = validated_data.pop('interests', [])
        
        group = Group.objects.create(created_by=user, **validated_data)
        group.interests.set(interests)
        
        # Add creator as admin
        GroupMember.objects.create(group=group, user=user, role='admin')
        
        return group


class GroupMemberSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)
    
    class Meta:
        model = GroupMember
        fields = ['id', 'user', 'role', 'joined_at']


class GroupMessageSerializer(serializers.ModelSerializer):
    sender = SimpleUserSerializer(read_only=True)
    
    class Meta:
        model = GroupMessage
        fields = ['id', 'group', 'sender', 'text', 'created_at']
        read_only_fields = ['id', 'created_at', 'sender', 'group']


class GroupJoinRequestSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer(read_only=True)
    group = GroupSerializer(read_only=True)
    
    class Meta:
        model = GroupJoinRequest
        fields = ['id', 'group', 'user', 'status', 'requested_at', 'processed_at']
        read_only_fields = ['id', 'requested_at', 'processed_at']


class GroupListSerializer(serializers.ModelSerializer):
    """Simplified serializer for group list view"""
    interests = InterestSerializer(many=True, read_only=True)
    member_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    join_request_status = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = [
            'id', 'name', 'description', 'interests', 'member_count',
            'is_member', 'join_request_status', 'last_message', 'created_at'
        ]
    
    def get_member_count(self, obj):
        return obj.members.count()
    
    def get_is_member(self, obj):
        user = self.context.get('current_user')
        if not user:
            return False
        return obj.members.filter(user=user).exists()
    
    def get_join_request_status(self, obj):
        user = self.context.get('current_user')
        if not user:
            return None
        request = obj.join_requests.filter(user=user).first()
        return request.status if request else None
    
    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return {
                'text': last_msg.text,
                'sender_username': last_msg.sender.username,
                'created_at': last_msg.created_at.isoformat()
            }
        return None