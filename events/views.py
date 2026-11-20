from django.shortcuts import render
from rest_framework import mixins, viewsets, permissions, status
from .serializers import EventSerializer, EventDetailSerializer
from .models import Event
from django.db import IntegrityError, transaction
from rest_framework.response import Response
from deliveres.services import (
    create_deliveries_for_event,
    enqueue_deliveries,
)
from rest_framework.throttling import ScopedRateThrottle
from deliveres.tasks import enqueue_deliveries
from django_filters.rest_framework import DjangoFilterBackend
from .filters import EventFilter

IDEMPOTENCY_CONSTRAINT = "unique_event_idempotency_per_owner"


def _is_idempotency_conflict(exc: IntegrityError) -> bool:
    diag = getattr(exc.__cause__, "diag", None)
    return getattr(diag, "constraint_name", None) == IDEMPOTENCY_CONSTRAINT

class EventViewSets(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = EventFilter

    http_method_names = ["get", "post", "head", "options"]

    def get_throttles(self):
        if self.action == "create":
            self.throttle_scope = "event_create"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        queryset = Event.objects.filter(owner=self.request.user)

        if self.action == "retrieve":
            queryset = queryset.prefetch_related("deliveries__endpoint")

        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return EventDetailSerializer
        return EventSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                event = serializer.save(owner=request.user)

                deliveries = create_deliveries_for_event(event)

                delivery_ids = [str(delivery.id) for delivery in deliveries]

                transaction.on_commit(
                    lambda: enqueue_deliveries(delivery_ids)
                )

        except IntegrityError as exc:
            if not _is_idempotency_conflict(exc):
                raise
            return Response(
                {"detail": "Event with this idempotency key already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        response_serializer = self.get_serializer(event)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=self.get_success_headers(response_serializer.data),
        )
