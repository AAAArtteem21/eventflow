from django.shortcuts import render
from rest_framework import mixins, viewsets, permissions, status
from .serializers import EventSerializer
from .models import Event
from django.db import IntegrityError, transaction
from rest_framework.response import Response


class EventViewSets(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Event.objects.filter(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                event = serializer.save(owner=request.user)

        except IntegrityError:
            return Response(
                {
                    "detail": (
                        "Event with this idempotency key already exists."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        response_serializer = self.get_serializer(event)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=self.get_success_headers(response_serializer.data),
        )
