from django.db import models
import uuid
from django.conf import settings

class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="events",)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    idempotency_key = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "idempotency_key"],
                name="unique_event_idempotency_per_owner",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
            models.Index(fields=["event_type"]),
        ]

    def __str__(self):
        return f"{self.event_type} ({self.owner})"
