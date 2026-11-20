from rest_framework import serializers
from rest_framework.serializers import ValidationError
from .models import Endpoint
from .validators import validate_endpoint_url

MAX_SUBSCRIBED_EVENTS = 50
MAX_EVENT_TYPE_LENGTH = 100


class EndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = Endpoint
        fields = [
            "id",
            "name",
            "url",
            "subscribed_events",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "is_active", "created_at"]

    def validate_url(self, value):
        validate_endpoint_url(value)
        return value

    def validate_subscribed_events(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError(
                "Subscribed events must be a list."
            )

        if not value:
            raise serializers.ValidationError(
                "At least one event type is required."
            )

        if len(value) > MAX_SUBSCRIBED_EVENTS:
            raise serializers.ValidationError(
                f"No more than {MAX_SUBSCRIBED_EVENTS} event types allowed."
            )

        cleaned = []
        for event in value:
            if not isinstance(event, str) or not event.strip():
                raise serializers.ValidationError(
                    "Each event must be a non-empty string."
                )
            event = event.strip()
            if len(event) > MAX_EVENT_TYPE_LENGTH:
                raise serializers.ValidationError(
                    f"Event type must be at most "
                    f"{MAX_EVENT_TYPE_LENGTH} characters."
                )
            cleaned.append(event)
        return list(dict.fromkeys(cleaned))