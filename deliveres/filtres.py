import django_filters

from deliveres.models import Delivery


class DeliveryFilter(django_filters.FilterSet):
    event = django_filters.UUIDFilter(field_name="event_id")
    endpoint = django_filters.UUIDFilter(field_name="endpoint_id")

    class Meta:
        model = Delivery
        fields = ["status", "event", "endpoint"]
