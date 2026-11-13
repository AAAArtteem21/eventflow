from django.shortcuts import render
from rest_framework import viewsets, permissions
from .serializers import EndpointSerializers
from .models import Endpoint


class EndpointViewSets(viewsets.ModelViewSet):
    serializer_class = EndpointSerializers
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Endpoint.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
