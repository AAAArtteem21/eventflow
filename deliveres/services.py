from .models import Delivery
from endpoints.models import Endpoint
import httpx
from django.db import transaction

def create_deliveries_for_event(event):
    endpoints = Endpoint.objects.filter(
        owner=event.owner,
        is_active=True,
        subscribed_events__contains=[event.event_type],
    )

    deliveries = [
        Delivery(
            event=event,
            endpoint=endpoint,
        )
        for endpoint in endpoints
    ]

    return Delivery.objects.bulk_create(deliveries)


def send_delivery(delivery: Delivery) -> Delivery:
    event = delivery.event
    payload = {
        "id": str(event.id),
        "event_type": event.event_type,
        "payload": event.payload,
        "created_at": event.created_at.isoformat(),
    }

    delivery.attempts += 1

    try:
        response = httpx.post(
            delivery.endpoint.url,
            json=payload,
            timeout=10.0
        )

        delivery.last_response_status = response.status_code
        delivery.last_error = None

        if 200 <= response.status_code < 300:
            delivery.status = Delivery.Status.SUCCESS
        else:
            delivery.status = Delivery.Status.FAILED
            delivery.last_error = (
                f"HTTP {response.status_code}: {response.text[:1000]}"
            )

    except httpx.TimeoutException as exc:
        delivery.status = Delivery.Status.FAILED
        delivery.last_error = "Request timeout"
        delivery.last_response_status = None

    except httpx.RequestError as exc:
        delivery.status = Delivery.Status.FAILED
        delivery.last_error = str(exc)[:1000]
        delivery.last_response_status = None

    delivery.next_retry_at = None
    delivery.save(
        update_fields=(
            "attempts",
            "status",
            "next_retry_at",
            "last_response_status",
            "last_error",
            "updated_at"
        )
    )

    return delivery

def enqueue_deliveries(delivery_ids):
    for delivery_id in delivery_ids:
        send_delivery_task.delay(delivery_id)


def claim_delivery(delivery_id):
    with transaction.atomic():
        delivery = Delivery.objects.select_for_update().get(id=delivery_id)
        if delivery.status != Delivery.Status.PENDING:
            return None
        delivery.status = Delivery.Status.PROCESSING
        delivery.save(
            update_fields = (
                "status",
            )
        )
    return delivery
    