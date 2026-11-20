from .models import DeliveryAttempt, Delivery
from rest_framework import serializers
from events.models import Event
from endpoints.models import Endpoint
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

class DeliveryEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "event_type",
        ]


class DeliveryEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = Endpoint
        fields = [
            "id",
            "name",
            "url"
        ]

class DeliverySerializer(serializers.ModelSerializer):
    event = DeliveryEventSerializer(read_only=True)
    endpoint = DeliveryEndpointSerializer(read_only=True)
    
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


class DeliveryAttemptInlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAttempt
        fields = [
            "id",
            "attempt_number",
            "response_status",
            "response_body",
            "error",
            "started_at",
            "finished_at",
        ]
        read_only_fields = fields

class DeliveryDetailSerializer(DeliverySerializer):
    attempt_history = DeliveryAttemptInlineSerializer(many=True, read_only=True)

    class Meta(DeliverySerializer.Meta):
        fields = DeliverySerializer.Meta.fields + ["attempt_history"]