from django.db.models import Q
from UserData.models import Users, Connection
from .models import ChatThread

def are_connected(u1: Users, u2: Users) -> bool:
    return Connection.objects.filter(
        Q(user=u1, connected_user=u2) | Q(user=u2, connected_user=u1)
    ).exists()


def get_or_create_thread(user1, user2):
    """Ensure thread exists between two users"""
    low, high = (user1, user2) if user1.id < user2.id else (user2, user1)
    thread, _ = ChatThread.objects.get_or_create(user_low=low, user_high=high)
    return thread