import django_filters

from .models import Event


class EventFilter(django_filters.FilterSet):
    created_after = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="date__gte",
    )
    created_before = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="date__lte",
    )

    class Meta:
        model = Event
        fields = ["event_type"]
