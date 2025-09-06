# groups/consumers.py - Fixed version

import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from Users.models import Users
from .models import Group, GroupMember, GroupMessage
from rest_framework_simplejwt.authentication import JWTAuthentication


def get_user_from_token(token):
    print("Validating token...")
    jwt_auth = JWTAuthentication()
    validated_token = jwt_auth.get_validated_token(token)
    user = jwt_auth.get_user(validated_token)
    print(f"Token valid for user: {user.id} ({user.phone_number})")
    return user


class GroupChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        print("\n" + "="*50)
        print("NEW GROUP WEBSOCKET CONNECTION ATTEMPT")
        print("="*50)
        
        print("URL Path:", self.scope.get("path"))
        print("Query String:", self.scope.get("query_string"))

        # Extract token
        query_string = self.scope["query_string"].decode()
        print("Raw token string:", query_string)

        # Parse query parameters
        query_params = {}
        if query_string:
            for param in query_string.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    query_params[key] = value
        
        token = query_params.get("token")
        print("Parsed token:", token[:50] + "..." if token and len(token) > 50 else token)

        # Authenticate user
        self.user = await self._get_user_from_token(token)
        print(f"Authenticated user: {self.user}")

        if not self.user:
            print("Authentication failed - closing connection")
            await self.close(code=4001)
            return

        # Get group ID
        try:
            self.group_id = self.scope["url_route"]["kwargs"]["group_id"]
            print(f"Group ID from URL: {self.group_id}")
        except KeyError as e:
            print(f"Missing group_id in URL: {e}")
            await self.close(code=4002)
            return

        # Get and validate group
        self.group = await self._get_group(self.user, int(self.group_id))
        print(f"Group object: {self.group}")

        if not self.group:
            print("Group not found or user not authorized")
            await self.close(code=4003)
            return

        # Verify user is a member
        is_member = await self._is_group_member(self.user, self.group)
        if not is_member:
            print(f"User {self.user.id} not a member of group {self.group.id}")
            await self.close(code=4004)
            return

        # Join room
        self.room_group_name = f"group_chat_{self.group.id}"
        print(f"Joining group room: {self.room_group_name}")

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        print("Group WebSocket connection accepted!")
        print(f"User {self.user.id} connected to group {self.group_id}")
        print("="*50 + "\n")

    async def disconnect(self, close_code):
        print(f"\nGroup WebSocket DISCONNECT - Code: {close_code}")
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            print(f"Left group room: {self.room_group_name}")

    async def receive_json(self, content, **kwargs):
        print(f"\nRECEIVED GROUP MESSAGE from user {self.user.id}:")
        print(f"   Content: {content}")
        
        if content.get("action") != "send":
            print("Invalid action - ignoring")
            return

        text = (content.get("text") or "").strip()
        if not text:
            print("Empty message - ignoring")
            return

        print(f"Creating group message: '{text}'")
        msg = await self._create_group_message(self.group.id, self.user.id, text)
        print(f"Group message created with ID: {msg['id']}")

        # Broadcast to group room
        broadcast_data = {
            "type": "group_chat_message",
            "payload": {
                "id": msg["id"],
                "group_id": msg["group_id"],
                "text": msg["text"],
                "created_at": msg["created_at"],
                "sender": msg["sender"],
            },
        }
        
        print(f"Broadcasting to group room {self.room_group_name}:")
        print(f"   Payload: {broadcast_data['payload']}")
        
        await self.channel_layer.group_send(self.room_group_name, broadcast_data)
        print("Group message broadcasted!")

    async def group_chat_message(self, event):
        print(f"\nSENDING GROUP MESSAGE to user {self.user.id}:")
        print(f"   Event: {event}")
        await self.send_json(event["payload"])
        print("Group message sent to WebSocket client!")

    # ---------- Database operations ----------
    @database_sync_to_async
    def _get_user_from_token(self, token):
        if not token:
            return None
        try:
            user = get_user_from_token(token)
            print(f"Database lookup successful: User {user.id}")
            return user
        except Exception as e:
            print(f"Token validation error: {e}")
            return None

    @database_sync_to_async
    def _get_group(self, user, group_id):
        try:
            group = Group.objects.get(pk=group_id, is_active=True)
            print(f"Group found: ID={group.id}, name={group.name}")
            return group
        except Group.DoesNotExist:
            print(f"Group {group_id} not found in database")
            return None

    @database_sync_to_async
    def _is_group_member(self, user, group):
        try:
            is_member = GroupMember.objects.filter(group=group, user=user).exists()
            print(f"Membership check: User {user.id} in group {group.id} = {is_member}")
            return is_member
        except Exception as e:
            print(f"Error checking membership: {e}")
            return False

    @database_sync_to_async
    def _create_group_message(self, group_id, sender_id, text):
        print(f"Creating group message in database:")
        print(f"   Group ID: {group_id}")
        print(f"   Sender ID: {sender_id}")
        print(f"   Text: '{text}'")
        
        try:
            # Get group and sender
            group = Group.objects.get(pk=group_id)
            sender = Users.objects.get(pk=sender_id)
            
            # Create message
            message = GroupMessage.objects.create(group=group, sender=sender, text=text)
            print(f"Group message created with ID: {message.id}")
            
            # Get sender details
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
            print(f"Error creating group message: {e}")
            raise