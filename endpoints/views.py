from rest_framework import viewsets, mixins, permissions
from rest_framework.exceptions import NotFound, MethodNotAllowed

from .serializers import EndpointSerializers
from .models import Endpoint


class EndpointViewSets(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = EndpointSerializers
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Endpoint.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def update(self, request, *args, **kwargs):
        self.get_object()
        raise MethodNotAllowed("PUT")

    def partial_update(self, request, *args, **kwargs):
        self.get_object()
        raise MethodNotAllowed("PATCH")

    def destroy(self, request, *args, **kwargs):
        self.get_object()
        raise MethodNotAllowed("DELETE")
