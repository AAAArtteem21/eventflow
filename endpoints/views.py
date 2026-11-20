from rest_framework import viewsets, mixins, permissions
from rest_framework.exceptions import NotFound, MethodNotAllowed
from rest_framework.decorators import action
from .serializers import EndpointSerializers
from .models import Endpoint


class EndpointViewSets(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = EndpointSerializers
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = [
        "get",
        "post",
        "patch",
        "head",
        "options",
    ]

    def get_queryset(self):
        return Endpoint.objects.filter(
            owner=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        endpoint = self.get_object()
        if endpoint.is_active:
            endpoint.is_active = False
            endpoint.save(update_fields=["is_active"])

        serializer = self.get_serializer(endpoint)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        endpoint = self.get_object()
        if not endpoint.is_active:
            endpoint.is_active = True
            endpoint.save(update_fields=["is_active"])

        serializer = self.get_serializer(endpoint)
        return Response(serializer.data)
