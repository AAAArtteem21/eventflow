from .models import DeliveryAttempt, Delivery
from rest_framework import serializers

class DeliverAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAttempt
        fields = [
            "id",
            "delivery",
            "attempt_number",
            "response_status",
            "response_body",
            "error",
            "started_at",
            "finished_at",
        ]
        read_only_fields = fields

class DeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = [
            "id",
            "event",
            "endpoint",
            "status",
            "attempts",
            "next_retry_at",
            "last_response_status",
            "last_error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
