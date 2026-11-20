from rest_framework import serializers
from .models import Event
from endpoints.models import Endpoint
from deliveres.models import Delivery

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "event_type",
            "payload",
            "idempotency_key",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]

class EventEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = Endpoint
        fields = ["id", "name", "url"]


class EventDeliverySerializer(serializers.ModelSerializer):
    endpoint = EventEndpointSerializer(read_only=True)

    class Meta:
        model = Delivery
        fields = [
            "id",
            "status",
            "attempts",
            "last_response_status",
            "last_error",
            "next_retry_at",
            "endpoint",
        ]


class EventDetailSerializer(EventSerializer):
    deliveries = EventDeliverySerializer(many=True, read_only=True)
    class Meta(EventSerializer.Meta):
        fields = [*EventSerializer.Meta.fields, "deliveries"]