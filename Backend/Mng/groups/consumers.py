# groups/consumers.py - Final Fixed Version

import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

from Users.models import Users
from .models import Group, GroupMember, GroupMessage
from rest_framework_simplejwt.authentication import JWTAuthentication


class GroupChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        print("\n" + "="*50)
        print("🚀 NEW GROUP WEBSOCKET CONNECTION ATTEMPT")
        print("="*50)
        
        # Extract token quickly
        token = self.scope["query_string"].decode()
        token = dict(q.split("=") for q in token.split("&") if "=" in q).get("token")

        # Get group ID early
        try:
            self.group_id = int(self.scope["url_route"]["kwargs"]["group_id"])
        except (KeyError, ValueError):
            await self.close(code=4002)
            return

        # Authenticate user and validate group/membership in one go
        auth_result = await self._authenticate_and_validate(token, self.group_id)
        
        if not auth_result:
            await self.close(code=4001)
            return
            
        self.user, self.group = auth_result

        # Join room and accept connection
        self.room_group_name = f"group_chat_{self.group.id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        print(f"✅ User {self.user.id} connected to group {self.group_id}")
        print("="*50 + "\n")

    async def disconnect(self, close_code):
        print(f"\n🔌 Group WebSocket DISCONNECT - Code: {close_code}")
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            print(f"👋 Left group room: {self.room_group_name}")

    async def receive_json(self, content, **kwargs):
        print(f"\n📨 RECEIVED GROUP MESSAGE from user {self.user.id}:")
        print(f"   Content: {content}")
        
        if content.get("action") != "send":
            print("❌ Invalid action - ignoring")
            return

        text = (content.get("text") or "").strip()
        if not text:
            print("❌ Empty message - ignoring")
            return

        print(f"💬 Creating group message: '{text}'")
        msg = await self._create_group_message(self.group.id, self.user.id, text)
        print(f"✅ Group message created with ID: {msg['id']}")

        # Broadcast to group room - use same structure as 2-person chat
        broadcast_data = {
            "type": "group_chat_message",
            # Send data directly instead of nested in payload
            "id": msg["id"],
            "group_id": msg["group_id"],
            "text": msg["text"],
            "created_at": msg["created_at"],
            "sender": msg["sender"],
        }
        
        print(f"📡 Broadcasting to group room {self.room_group_name}:")
        print(f"   Data: {broadcast_data}")
        
        await self.channel_layer.group_send(self.room_group_name, broadcast_data)
        print("✅ Group message broadcasted!")

    async def group_chat_message(self, event):
        print(f"\n📤 SENDING GROUP MESSAGE to user {self.user.id}:")
        print(f"   Event: {event}")
        
        # Send message data directly (not wrapped in payload)
        message_data = {
            "id": event["id"],
            "group_id": event["group_id"], 
            "text": event["text"],
            "created_at": event["created_at"],
            "sender": event["sender"],
        }
        
        await self.send_json(message_data)
        print("✅ Group message sent to WebSocket client!")

    # ---------- Database operations ----------
    @database_sync_to_async
    def _authenticate_and_validate(self, token, group_id):
        """Single database query to authenticate user and validate group membership"""
        if not token:
            return None
        
        try:
            # Authenticate user
            print("🔑 Validating token...")
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token)
            user = jwt_auth.get_user(validated_token)
            print(f"✅ Token valid for user: {user.id}")
            
            # Get group and check membership in single query using select_related
            group = Group.objects.select_related().prefetch_related('members').get(
                pk=group_id, 
                is_active=True,
                members__user=user  # This ensures user is a member
            )
            
            print(f"✅ Authenticated user {user.id} for group {group.name}")
            return (user, group)
            
        except (Group.DoesNotExist, Exception) as e:
            print(f"❌ Authentication/validation failed: {e}")
            return None

    @database_sync_to_async
    def _create_group_message(self, group_id, sender_id, text):
        try:
            # Use get_or_create or direct creation with minimal queries
            group = Group.objects.get(pk=group_id)
            sender = Users.objects.select_related('profile').prefetch_related('photos').get(pk=sender_id)
            
            # Create message
            message = GroupMessage.objects.create(group=group, sender=sender, text=text)
            
            # Get sender details efficiently
            photo = None
            if hasattr(sender, "photos") and sender.photos.exists():
                first_photo = sender.photos.filter(is_private=False).first()
                if first_photo:
                    photo = first_photo.url

            full_name = ""
            if hasattr(sender, "profile") and sender.profile:
                full_name = sender.profile.full_name

            return {
                "id": message.id,
                "group_id": group.id,
                "text": message.text,
                "created_at": message.created_at.isoformat(),
                "sender": {
                    "id": sender.id,
                    "username": sender.username,
                    "full_name": full_name,
                    "photo": photo,
                },
            }
        except Exception as e:
            print(f"❌ Error creating group message: {e}")
            raise