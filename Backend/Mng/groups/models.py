# Groups/models.py - Create this file

from django.db import models
from Users.models import Users, Interest

class Group(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    interests = models.ManyToManyField(Interest, related_name="groups", blank=True)
    created_by = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="created_groups")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def member_count(self):
        return self.members.count()


class GroupMember(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]
    
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="group_memberships")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('group', 'user')
        indexes = [
            models.Index(fields=['group', 'user']),
        ]
    
    def __str__(self):
        return f"{self.user.username} in {self.group.name} ({self.role})"


class GroupMessage(models.Model):
    group = models.ForeignKey(Group, related_name="messages", on_delete=models.CASCADE)
    sender = models.ForeignKey(Users, related_name="group_messages", on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['group', '-created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"[{self.group.name}] {self.sender.username}: {self.text[:30]}"


class GroupJoinRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="join_requests")
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="group_join_requests")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(Users, on_delete=models.SET_NULL, null=True, blank=True, related_name="processed_requests")
    
    class Meta:
        unique_together = ('group', 'user')
        indexes = [
            models.Index(fields=['group', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} → {self.group.name} ({self.status})"