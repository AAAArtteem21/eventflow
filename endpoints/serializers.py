from rest_framework import serializers
from rest_framework.serializers import ValidationError
from .models import Endpoint

class EndpointSerializers(serializers.ModelSerializer):
    class Meta:
        model = Endpoint
        fields = [
            "id",
            "name",
            "url",
            "is_active",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]
