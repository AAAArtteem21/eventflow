import django_filters

from deliveres.models import Delivery


class DeliveryFilter(django_filters.FilterSet):
    event = django_filters.UUIDFilter(field_name="event_id")
    endpoint = django_filters.UUIDFilter(field_name="endpoint_id")

    created_after = django_filters.DateFilter(
    field_name="created_at",
    lookup_expr="date__gte",
    )
    created_before = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="date__lte",
    )

    class Meta:
        model = Delivery
        fields = ["status", "event", "endpoint"]
