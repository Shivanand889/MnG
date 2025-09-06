import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

from Users.models import Users
from .utils import get_or_create_thread, are_connected
from .models import Message, ChatThread
from rest_framework_simplejwt.authentication import JWTAuthentication


def get_user_from_token(token):
    print("🔑 Validating token...")
    jwt_auth = JWTAuthentication()
    validated_token = jwt_auth.get_validated_token(token)
    user = jwt_auth.get_user(validated_token)
    print(f"✅ Token valid for user: {user.id} ({user.phone_number})")
    return user


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        print("\n" + "="*50)
        print("🚀 NEW WEBSOCKET CONNECTION ATTEMPT")
        print("="*50)
        
        print("📍 URL Path:", self.scope.get("path"))
        print("📍 Query String:", self.scope.get("query_string"))

        # Extract token
        token = self.scope["query_string"].decode()
        print("🔍 Raw token string:", token)

        token = dict(q.split("=") for q in token.split("&") if "=" in q).get("token")
        print("🔍 Parsed token:", token[:50] + "..." if token and len(token) > 50 else token)

        # Authenticate user
        self.user = await self._get_user_from_token(token)
        print(f"👤 Authenticated user: {self.user}")

        if not self.user:
            print("❌ Authentication failed - closing connection")
            await self.close(code=4001)
            return

        # Get thread ID
        try:
            self.thread_id = self.scope["url_route"]["kwargs"]["thread_id"]
            print(f"🧵 Thread ID from URL: {self.thread_id}")
        except KeyError as e:
            print(f"❌ Missing thread_id in URL: {e}")
            await self.close(code=4002)
            return

        # Get and validate thread
        self.thread = await self._get_thread(self.user, int(self.thread_id))
        print(f"🧵 Thread object: {self.thread}")

        if not self.thread:
            print("❌ Thread not found or user not authorized")
            await self.close(code=4003)
            return

        # Verify user access
        if not self.thread.has_user(self.user):
            print(f"❌ User {self.user.id} not authorized for thread {self.thread.id}")
            print(f"   Thread participants: user_low={self.thread.user_low_id}, user_high={self.thread.user_high_id}")
            await self.close(code=4004)
            return

        # Join room
        self.room_group_name = f"chat_{self.thread.id}"
        print(f"🏠 Joining room: {self.room_group_name}")

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        
        print("✅ WebSocket connection accepted!")
        print(f"🔗 User {self.user.id} connected to thread {self.thread_id}")
        print("="*50 + "\n")

    async def disconnect(self, close_code):
        print(f"\n🔌 WebSocket DISCONNECT - Code: {close_code}")
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            print(f"👋 Left room: {self.room_group_name}")

    async def receive_json(self, content, **kwargs):
        print(f"\n📨 RECEIVED MESSAGE from user {self.user.id}:")
        print(f"   Content: {content}")
        
        if content.get("action") != "send":
            print("❌ Invalid action - ignoring")
            return

        text = (content.get("text") or "").strip()
        if not text:
            print("❌ Empty message - ignoring")
            return

        print(f"💬 Creating message: '{text}'")
        msg = await self._create_message(self.thread.id, self.user.id, text)
        print(f"✅ Message created with ID: {msg['id']}")

        # Broadcast to room
        broadcast_data = {
            "type": "chat.message",
            "payload": {
                "id": msg["id"],
                "thread": msg["thread"],
                "text": msg["text"],
                "created_at": msg["created_at"],
                "sender": msg["sender"],
            },
        }
        
        print(f"📡 Broadcasting to room {self.room_group_name}:")
        print(f"   Payload: {broadcast_data['payload']}")
        
        await self.channel_layer.group_send(self.room_group_name, broadcast_data)
        print("✅ Message broadcasted!")

    async def chat_message(self, event):
        print(f"\n📤 SENDING MESSAGE to user {self.user.id}:")
        print(f"   Event: {event}")
        await self.send_json(event["payload"])
        print("✅ Message sent to WebSocket client!")

    # ---------- Database operations ----------
    @database_sync_to_async
    def _get_user_from_token(self, token):
        if not token:
            return None
        try:
            user = get_user_from_token(token)
            print(f"🔍 Database lookup successful: User {user.id}")
            return user
        except Exception as e:
            print(f"❌ Token validation error: {e}")
            return None

    @database_sync_to_async
    def _get_thread(self, user, thread_id):
        try:
            thread = ChatThread.objects.get(pk=thread_id)
            print(f"🔍 Thread found: ID={thread.id}, user_low={thread.user_low_id}, user_high={thread.user_high_id}")
            
            # Check if user is participant
            if thread.has_user(user):
                print(f"✅ User {user.id} is authorized for this thread")
                return thread
            else:
                print(f"❌ User {user.id} is NOT authorized for this thread")
                return None
        except ChatThread.DoesNotExist:
            print(f"❌ Thread {thread_id} not found in database")
            return None

    @database_sync_to_async
    def _create_message(self, thread_id, sender_id, text):
        print(f"💾 Creating message in database:")
        print(f"   Thread ID: {thread_id}")
        print(f"   Sender ID: {sender_id}")
        print(f"   Text: '{text}'")
        
        try:
            # Get thread and sender
            thread = ChatThread.objects.get(pk=thread_id)
            sender = Users.objects.get(pk=sender_id)
            
            # Create message
            message = Message.objects.create(thread=thread, sender=sender, text=text)
            print(f"✅ Message created with ID: {message.id}")
            
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
                "thread": thread.id,
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
            print(f"❌ Error creating message: {e}")
            raise