from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import DeliveryAttempt
from .serializers import DeliverAttemptSerializer


class DeliveryAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DeliverAttemptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = DeliveryAttempt.objects.filter(
            delivery__event__owner=self.request.user
        ).select_related(
            "delivery",
            "delivery__event",
        )

        delivery_id = self.request.query_params.get("delivery_id")

        if delivery_id:
            queryset = queryset.filter(
                delivery_id=delivery_id
            )

        return queryset.order_by("attempt_number")
