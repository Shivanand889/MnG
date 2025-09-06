from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission

from django.db import models
from django.utils import timezone
from datetime import timedelta

from Users.models import Users
# Connections between users
class Connection(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="connections")
    connected_user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="connected_to")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "connected_user")  # prevent duplicates

    def __str__(self):
        return f"{self.user.username} ↔ {self.connected_user.username}"


# Connection requests
class ConnectionRequest(models.Model):
    from_user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="sent_requests")
    to_user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="received_requests")

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("from_user", "to_user")  # prevent duplicate requests

    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username} ({self.status})"

