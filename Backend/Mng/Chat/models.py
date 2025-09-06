from django.db import models
from Users.models import Users


class ChatThread(models.Model):
    """
    One-to-one thread between two users.
    We always store the smaller user id as user_low to guarantee uniqueness.
    """
    user_low  = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="threads_low")
    user_high = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="threads_high")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user_low", "user_high")
        indexes = [
            models.Index(fields=["user_low", "user_high"]),
        ]

    def participants(self):
        return (self.user_low, self.user_high)

    def has_user(self, user):
        return user == self.user_low or user == self.user_high

    def __str__(self):
        return f"Thread {self.pk}: {self.user_low_id} ↔ {self.user_high_id}"


class Message(models.Model):
    thread = models.ForeignKey(ChatThread, related_name="messages", on_delete=models.CASCADE)
    sender = models.ForeignKey(Users, related_name="sent_messages", on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["thread", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.thread_id}] {self.sender_id}: {self.text[:30]}"
