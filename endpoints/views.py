from rest_framework import viewsets, mixins, permissions
from rest_framework.exceptions import NotFound, MethodNotAllowed
from rest_framework.decorators import action
from .serializers import EndpointSerializer, EndpointCreateSerializer
from .models import Endpoint
from drf_spectacular.utils import extend_schema, extend_schema_view

class EndpointViewSets(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = EndpointSerializer
    permission_classes = [permissions.IsAuthenticated]

    http_method_names = [
        "get",
        "post",
        "patch",
        "head",
        "options",
    ]

    def get_serializer_class(self):
        if self.action in ("create", "rotate_secret"):
            return EndpointCreateSerializer
        return EndpointSerializer

    def get_queryset(self):
        return Endpoint.objects.filter(
            owner=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @extend_schema(
        summary="Деактивировать endpoint",
        description=(
            "Прекращает доставку на этот endpoint. Уже созданные доставки "
            "получат статус FAILED с ошибкой `Endpoint is inactive`."
        ),
        request=None,
        responses={200: EndpointSerializer},
    )
    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        endpoint = self.get_object()
        if endpoint.is_active:
            endpoint.is_active = False
            endpoint.save(update_fields=["is_active"])

        serializer = self.get_serializer(endpoint)
        return Response(serializer.data)

    @extend_schema(
        summary="Активировать endpoint",
        description="Возобновляет доставку. Операция идемпотентна.",
        request=None,
        responses={200: EndpointSerializer},
    )
    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        endpoint = self.get_object()
        if not endpoint.is_active:
            endpoint.is_active = True
            endpoint.save(update_fields=["is_active"])

        serializer = self.get_serializer(endpoint)
        return Response(serializer.data)

    @extend_schema(
        summary="Выпустить новый secret",
        description=(
            "Генерирует новый secret и показывает его в ответе **один раз**. "
            "Старый secret перестаёт действовать сразу. Доставки, которые "
            "уже в очереди или ждут повтора, будут подписаны новым secret."
        ),
        request=None,
        responses={200: EndpointCreateSerializer},
    )
    @action(detail=True, methods=["post"], url_path="rotate-secret")
    def rotate_secret(self, request, pk=None):
        endpoint = self.get_object()
        endpoint.secret = generate_endpoint_secret()
        endpoint.save(update_fields=["secret"])
        serializer = self.get_serializer(endpoint)
        return Response(serializer.data)
