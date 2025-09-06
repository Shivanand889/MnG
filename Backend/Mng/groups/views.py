# groups/views.py - Fixed version

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Group, GroupMember, GroupMessage, GroupJoinRequest
from Users.models import Interest  # Import Interest from Users app
from .serializers import (
    GroupSerializer, CreateGroupSerializer, GroupListSerializer,
    GroupMemberSerializer, GroupMessageSerializer, GroupJoinRequestSerializer
)
from Users.serializers import InterestSerializer  # Import from Users serializers


def get_user_from_token(token):
    print("🔑 Validating token...")
    jwt_auth = JWTAuthentication()
    validated_token = jwt_auth.get_validated_token(token)
    user = jwt_auth.get_user(validated_token)
    print(f"✅ Token valid for user: {user.id} ({user.phone_number})")
    return user


@api_view(['POST'])
def create_group(request):
    """Create a new group"""
    access_token = request.data.get("access_token")
    if not access_token:
        return Response({"error": "Access token required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = get_user_from_token(access_token)
    except Exception as e:
        return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Get group data
    name = request.data.get('name', '').strip()
    description = request.data.get('description', '').strip()
    interests_data = request.data.get('interests', [])
    
    if not name:
        return Response({"error": "Group name is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Create the group
        group = Group.objects.create(
            name=name,
            description=description,
            created_by=user
        )
        
        # Handle interests - create them if they don't exist
        if interests_data:
            for interest_name in interests_data:
                interest_name = interest_name.strip()
                if interest_name:
                    interest, created = Interest.objects.get_or_create(name=interest_name)
                    group.interests.add(interest)
        
        # Add creator as admin
        GroupMember.objects.create(group=group, user=user, role='admin')
        
        # Return group data
        group_data = GroupSerializer(group, context={'current_user': user}).data
        return Response(group_data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        print(f"Error creating group: {e}")
        return Response({"error": "Failed to create group"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def get_groups(request):
    """Get all groups with user's membership status"""
    access_token = request.data.get("access_token")
    if not access_token:
        return Response({"error": "Access token required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = get_user_from_token(access_token)
    except Exception as e:
        return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
    
    groups = Group.objects.filter(is_active=True).prefetch_related(
        'interests', 'members', 'messages', 'join_requests'
    )
    
    serializer = GroupListSerializer(groups, many=True, context={'current_user': user})
    return Response({'results': serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_user_groups(request):
    """Get groups user is a member of"""
    access_token = request.GET.get("access_token") or request.data.get("access_token")
    if not access_token:
        return Response({"error": "Access token required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = get_user_from_token(access_token)
    except Exception as e:
        return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
    
    user_groups = Group.objects.filter(
        members__user=user, is_active=True
    ).prefetch_related('interests', 'members', 'messages')
    
    serializer = GroupListSerializer(user_groups, many=True, context={'current_user': user})
    return Response({'results': serializer.data}, status=status.HTTP_200_OK)


@api_view(['POST'])
def join_group(request, group_id):
    """Request to join a group"""
    access_token = request.data.get("access_token")
    if not access_token:
        return Response({"error": "Access token required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = get_user_from_token(access_token)
    except Exception as e:
        return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        group = Group.objects.get(pk=group_id, is_active=True)
    except Group.DoesNotExist:
        return Response({"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if already a member
    if group.members.filter(user=user).exists():
        return Response({"error": "Already a member"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if join request already exists
    existing_request = group.join_requests.filter(user=user).first()
    if existing_request:
        if existing_request.status == 'pending':
            return Response({"error": "Join request already pending"}, status=status.HTTP_400_BAD_REQUEST)
    
    # For now, auto-approve join requests (you can modify this logic)
    GroupMember.objects.create(group=group, user=user, role='member')
    
    return Response({"message": "Successfully joined group"}, status=status.HTTP_200_OK)


@api_view(['POST'])
def leave_group(request, group_id):
    """Leave a group"""
    access_token = request.data.get("access_token")
    if not access_token:
        return Response({"error": "Access token required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = get_user_from_token(access_token)
    except Exception as e:
        return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        group = Group.objects.get(pk=group_id, is_active=True)
        membership = group.members.get(user=user)
        
        # Prevent creator from leaving if they're the only admin
        if membership.role == 'admin':
            admin_count = group.members.filter(role='admin').count()
            if admin_count == 1 and group.created_by == user:
                return Response(
                    {"error": "Cannot leave as the only admin. Transfer admin rights first."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        membership.delete()
        return Response({"message": "Left group successfully"}, status=status.HTTP_200_OK)
        
    except Group.DoesNotExist:
        return Response({"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND)
    except GroupMember.DoesNotExist:
        return Response({"error": "Not a member of this group"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_group_messages(request, group_id):
    """Get messages for a specific group"""
    access_token = request.GET.get("access_token") or request.data.get("access_token")
    if not access_token:
        return Response({"error": "Access token required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = get_user_from_token(access_token)
    except Exception as e:
        return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        group = Group.objects.get(pk=group_id, is_active=True)
        
        # Check if user is a member
        if not group.members.filter(user=user).exists():
            return Response(
                {"error": "Not authorized to view group messages"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        messages = GroupMessage.objects.filter(group=group).select_related(
            'sender', 'sender__profile'
        ).order_by('created_at')
        
        message_data = []
        for msg in messages:
            # Get sender photo
            photo = None
            if hasattr(msg.sender, 'photos') and msg.sender.photos.exists():
                first_photo = msg.sender.photos.filter(is_private=False).first()
                if first_photo:
                    photo = first_photo.url
            
            # Get full name
            full_name = ""
            if hasattr(msg.sender, 'profile') and msg.sender.profile:
                full_name = msg.sender.profile.full_name
            
            message_data.append({
                "id": msg.id,
                "text": msg.text,
                "created_at": msg.created_at.isoformat(),
                "sender": {
                    "id": msg.sender.id,
                    "username": msg.sender.username,
                    "full_name": full_name,
                    "photo": photo,
                }
            })
        
        return Response({
            "group_id": group_id,
            "group_name": group.name,
            "message_count": len(message_data),
            "results": message_data
        })
        
    except Group.DoesNotExist:
        return Response({"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def send_group_message(request, group_id):
    """Send a message to a group (REST API fallback)"""
    access_token = request.data.get("access_token")
    message_text = request.data.get("message")
    
    if not access_token:
        return Response({"error": "Access token required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = get_user_from_token(access_token)
    except Exception as e:
        return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
    
    if not message_text:
        return Response({"error": "Message text required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        group = Group.objects.get(pk=group_id, is_active=True)
        
        # Check if user is a member
        if not group.members.filter(user=user).exists():
            return Response(
                {"error": "Not authorized to send messages to this group"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create message
        message = GroupMessage.objects.create(
            group=group,
            sender=user,
            text=message_text
        )
        
        # Get sender details for broadcast
        photo = None
        if hasattr(user, 'photos') and user.photos.exists():
            first_photo = user.photos.filter(is_private=False).first()
            if first_photo:
                photo = first_photo.url
        
        full_name = ""
        if hasattr(user, 'profile') and user.profile:
            full_name = user.profile.full_name
        
        # Broadcast to WebSocket group
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"group_chat_{group_id}",
            {
                "type": "group_chat_message",
                "payload": {
                    "id": message.id,
                    "group_id": group.id,
                    "text": message.text,
                    "created_at": message.created_at.isoformat(),
                    "sender": {
                        "id": user.id,
                        "username": user.username,
                        "full_name": full_name,
                        "photo": photo,
                    },
                },
            },
        )
        
        return Response(
            GroupMessageSerializer(message).data,
            status=status.HTTP_201_CREATED
        )
        
    except Group.DoesNotExist:
        return Response({"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_group_members(request, group_id):
    """Get members of a group"""
    access_token = request.GET.get("access_token") or request.data.get("access_token")
    if not access_token:
        return Response({"error": "Access token required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = get_user_from_token(access_token)
    except Exception as e:
        return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        group = Group.objects.get(pk=group_id, is_active=True)
        
        # Check if user is a member
        if not group.members.filter(user=user).exists():
            return Response(
                {"error": "Not authorized to view group members"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        members = group.members.select_related('user', 'user__profile').all()
        serializer = GroupMemberSerializer(members, many=True)
        
        return Response({
            "group_id": group_id,
            "group_name": group.name,
            "members": serializer.data
        })
        
    except Group.DoesNotExist:
        return Response({"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_interests(request):
    """Get all available interests"""
    interests = Interest.objects.all().order_by('name')
    serializer = InterestSerializer(interests, many=True)
    return Response({'results': serializer.data}, status=status.HTTP_200_OK)


@api_view(['POST'])
def create_interest(request):
    """Create a new interest (admin only or allow users to suggest)"""
    access_token = request.data.get("access_token")
    if not access_token:
        return Response({"error": "Access token required"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        user = get_user_from_token(access_token)
    except Exception as e:
        return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
    
    name = request.data.get('name', '').strip()
    if not name:
        return Response({"error": "Interest name is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if interest already exists
    if Interest.objects.filter(name__iexact=name).exists():
        return Response({"error": "Interest already exists"}, status=status.HTTP_400_BAD_REQUEST)
    
    interest = Interest.objects.create(name=name)
    serializer = InterestSerializer(interest)
    return Response(serializer.data, status=status.HTTP_201_CREATED)