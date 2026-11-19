from rest_framework import serializers
from rest_framework.serializers import ValidationError
from .models import Endpoint
from .validators import validate_endpoint_url

class EndpointSerializer(serializers.ModelSerializer):
    url = serializers.URLField(
        validators=[validate_endpoint_url],
    )

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
        read_only_fields = ["id", "created_at"]
