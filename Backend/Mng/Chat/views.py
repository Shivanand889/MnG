from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework_simplejwt.authentication import JWTAuthentication

from UserData.models import Users
from .serializers import MessageSerializer
from .utils import get_or_create_thread, are_connected

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ChatThread, Message



def get_user_from_token(token):
    
    print("11111111111")
    jwt_auth = JWTAuthentication()
    validated_token = jwt_auth.get_validated_token(token)  # Validate and decode
    user = jwt_auth.get_user(validated_token)  # Get user instance
    return user


@api_view(["POST"])
def chat(request):
    """
    Body:
    {
      "access_token": "...",   # current user (sender)
      "receiver_id": 123,      # other user
      "message": "Hello"
    }
    """
    access_token = request.data.get("access_token")
    receiver_id  = request.data.get("receiver_id")
    message_text = request.data.get("message")

    if not access_token or not receiver_id or not message_text:
        return Response({"error": "Missing fields"}, status=status.HTTP_400_BAD_REQUEST)

    sender = get_user_from_token(access_token)
    if not sender:
        return Response({"error": "Invalid or expired access token"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        receiver = Users.objects.get(pk=receiver_id)
    except Users.DoesNotExist:
        return Response({"error": "Receiver not found"}, status=status.HTTP_404_NOT_FOUND)

    # Optional: enforce only connected users can chat
    if not are_connected(sender, receiver):
        return Response({"error": "Not allowed to chat with this user"}, status=status.HTTP_403_FORBIDDEN)

    # Get/Create thread and persist message
    thread = get_or_create_thread(sender, receiver)
    from .models import Message
    msg = Message.objects.create(thread=thread, sender=sender, text=message_text)

    # Fan-out to WebSocket group
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{thread.id}",
        {
            "type": "chat.message",
            "payload": {
                "id": msg.id,
                "thread": thread.id,
                "text": msg.text,
                "created_at": msg.created_at.isoformat(),
                "sender": {
                    "id": sender.id,
                    "username": sender.username,
                    "full_name": getattr(sender.profile, "full_name", ""),
                    "photo": (sender.photos.filter(is_private=False).first().url
                              if hasattr(sender, "photos") and sender.photos.exists()
                              else None),
                },
            },
        },
    )

    return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def thread_messages(request, thread_id):
    from .models import ChatThread
    try:
        thread = ChatThread.objects.get(pk=thread_id)
    except ChatThread.DoesNotExist:
        return Response({"detail": "Not found"}, status=404)
    msgs = thread.messages.select_related("sender").order_by("-created_at")[:100]
    return Response(MessageSerializer(msgs, many=True).data)


# Add this to your Chat/views.py



@api_view(['GET'])
def get_thread_messages(request, thread_id):
    """
    Get all messages for a specific thread
    """
    print(f"\n📋 API: Getting messages for thread {thread_id}")
    print(f"👤 Requested by user: {request.user.id}")
    
    # Get thread
    try:
        thread = ChatThread.objects.get(pk=thread_id)
        print(f"✅ Thread found: {thread}")
    except ChatThread.DoesNotExist:
        print("❌ Thread not found")
        return Response(
            {"error": "Thread not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if user is part of this thread
    if not thread.has_user(request.user):
        print(f"❌ User {request.user.id} not authorized for thread {thread_id}")
        return Response(
            {"error": "Not authorized"}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get messages
    messages = Message.objects.filter(thread=thread).select_related('sender', 'sender__profile').order_by('created_at')
    print(f"📨 Found {messages.count()} messages")
    
    # Serialize messages
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
            "is_read": msg.is_read,
            "sender": {
                "id": msg.sender.id,
                "username": msg.sender.username,
                "full_name": full_name,
                "photo": photo,
            }
        })
    
    return Response({
        "thread_id": thread_id,
        "message_count": len(message_data),
        "results": message_data
    })


@api_view(['GET'])
def get_user_threads(request):
    """
    Get all threads for the current user
    """
    access_token = request.data.get("access_token")
    if not access_token:
        return Response({"error": "Access token required"}, status=status.HTTP_400_BAD_REQUEST)

    # Decode token and get user_id
    user = get_user_from_token(access_token)

    if not user:
        return Response({"error": "Invalid or expired access token"}, status=status.HTTP_401_UNAUTHORIZED)

    print(f"\n📋 API: Getting threads for user {user.id}")
    
    # Get all threads where user is a participant
    threads = ChatThread.objects.filter(
        models.Q(user_low=user) | models.Q(user_high=user)
    ).order_by('-created_at')
    
    thread_data = []
    for thread in threads:
        # Get other participant
        other_user = thread.user_high if thread.user_low == user else thread.user_low
        
        # Get last message
        last_message = thread.messages.order_by('-created_at').first()
        last_message_data = None
        if last_message:
            last_message_data = {
                "text": last_message.text,
                "created_at": last_message.created_at.isoformat(),
                "sender_username": last_message.sender.username
            }
        
        # Get other user photo
        photo = None
        if hasattr(other_user, 'photos') and other_user.photos.exists():
            first_photo = other_user.photos.filter(is_private=False).first()
            if first_photo:
                photo = first_photo.url
        
        # Get full name
        full_name = ""
        if hasattr(other_user, 'profile') and other_user.profile:
            full_name = other_user.profile.full_name
        
        thread_data.append({
            "id": thread.id,
            "other_user": {
                "id": other_user.id,
                "username": other_user.username,
                "full_name": full_name,
                "photo": photo,
            },
            "last_message": last_message_data,
            "created_at": thread.created_at.isoformat(),
        })
    
    print(f"📨 Found {len(thread_data)} threads")
    return Response({"results": thread_data})


