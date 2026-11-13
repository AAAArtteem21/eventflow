from django.db import models
from django.conf import settings
import uuid
import secrets

def generate_endpoints_secret():
    return secrets.token_urlsafe(32)

class Endpoint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="endpoints",)
    name = models.CharField(max_length=100)
    url = models.URLField()
    secret = models.CharField(max_length=64, default=generate_endpoints_secret, editable=True)
    is_active = models.BooleanField(default=True)
    subscribed_events = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.owner})"