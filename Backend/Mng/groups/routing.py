from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"wss://mng-gywl.onrender.com/ws/group-chat/(?P<group_id>\d+)/$", consumers.GroupChatConsumer.as_asgi()),
]
