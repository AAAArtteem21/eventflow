from django.db import models
import uuid
from django.conf import settings
from events.models import Event
from endpoints.models import Endpoint

class Delivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="deliveries")
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE, related_name="deliveries")
    status = models.CharField(max_length=20,choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    last_response_status = models.PositiveSmallIntegerField(null=True,blank=True)
    last_error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta: 
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["event", "endpoint"],
                name="unique_delivery_per_event_endpoint",
            ),
        ]

        indexes = models.Index(
            fields = ["status","next_retry_at"],
            name="delivery_status_retry_idx",
        ),
        models.Index(
            fields=("endpoint", "-created_at"),
            name="delivery_endpoint_created_idx",
        ),

    def __str__(self):
        return (
            f"Delivery {self.id}:"
            f"{self.event.event_type} -> {self.endpoint.name}"
        )


class DeliveryAttempt(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    delivery = models.ForeignKey(
        "deliveres.Delivery",
        on_delete=models.CASCADE,
        related_name="attempt_history",
    )

    attempt_number = models.PositiveIntegerField()

    response_status = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    response_body = models.TextField(
        blank=True,
        default="",
    )

    error = models.TextField(
        null=True,
        blank=True,
    )

    started_at = models.DateTimeField(auto_now_add=True)

    finished_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["attempt_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["delivery", "attempt_number"],
                name="unique_delivery_attempt_number",
            ),
        ]
