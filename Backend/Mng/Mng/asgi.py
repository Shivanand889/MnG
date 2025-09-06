import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Mng.settings")
django.setup()

# Import both routing files
import Chat.routing
import groups.routing

# Combine websocket URL patterns from both apps
websocket_patterns = Chat.routing.websocket_urlpatterns + groups.routing.websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_patterns)
    ),
})