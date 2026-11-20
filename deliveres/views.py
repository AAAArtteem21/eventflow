from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .services import retry_delivery
from .models import DeliveryAttempt, Delivery
from .serializers import DeliverAttemptSerializer, DeliverySerializer
from deliveres.filtres import DeliveryFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

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


class DeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = DeliveryFilter

    ordering_fields = ["created_at", "updated_at", "attempts"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            Delivery.objects
            .filter(event__owner=self.request.user)
            .select_related("event", "endpoint")
        )

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        delivery = self.get_object()

        try:
            delivery = retry_delivery(
                delivery_id=delivery.id,
                user=request.user
            )
        except Exception as exc:
            return Response(
                {"detail": str(exc.message)},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = self.get_serializer(delivery)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
