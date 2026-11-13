from django.shortcuts import render
from rest_framework import viewsets, permissions
from .serializers import EventSerializer
from .models import Event


class EventViewSets(viewsets.ModelViewSet):
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Event.objects.filter(owner=self.request.user)

    def perform_create(self, serializers):
        serializers.save(owner=self.request.user)
