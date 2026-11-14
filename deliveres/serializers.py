from .models import DeliveryAttempt
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