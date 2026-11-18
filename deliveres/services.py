from .models import Delivery
from endpoints.models import Endpoint
import httpx
import uuid
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta

MAX_ATTEMPTS = 8

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
    should_retry = False

    try:
        response = httpx.post(
            delivery.endpoint.url,
            json=payload,
            timeout=10.0,
        )

        delivery.last_response_status = response.status_code

        if 200 <= response.status_code < 300:
            delivery.status = Delivery.Status.SUCCESS
            delivery.last_error = None

        else:
            delivery.status = Delivery.Status.FAILED
            delivery.last_error = (
                f"HTTP {response.status_code}: {response.text[:1000]}"
            )
            should_retry = is_retryable_status(response.status_code)

    except httpx.TimeoutException:
        delivery.status = Delivery.Status.FAILED
        delivery.last_error = "Request timed out"
        delivery.last_response_status = None
        should_retry = True

    except httpx.RequestError as exc:
        delivery.status = Delivery.Status.FAILED
        delivery.last_error = str(exc)[:1000]
        delivery.last_response_status = None
        should_retry = True

    if delivery.status == Delivery.Status.SUCCESS:
        delivery.next_retry_at = None

    elif should_retry and delivery.attempts < MAX_ATTEMPTS:
        delay = get_retry_delay(delivery.attempts)

        delivery.next_retry_at = (
            timezone.now() + timezone.timedelta(seconds=delay)
        )

    else:
        delivery.next_retry_at = None

    delivery.save(
        update_fields=[
            "attempts",
            "status",
            "last_response_status",
            "last_error",
            "next_retry_at",
            "updated_at",
        ]
    )

    return delivery

def enqueue_deliveries(delivery_ids):
    for delivery_id in delivery_ids:
        send_delivery_task.delay(delivery_id)


def claim_delivery(delivery_id):
    with transaction.atomic():
        now = timezone.now()
        delivery = Delivery.objects.select_for_update().get(id=delivery_id)
        is_pending = delivery.status == Delivery.Status.PENDING
        is_retry_ready = (
            delivery.status == Delivery.Status.FAILED
            and delivery.next_retry_at is not None
            and delivery.next_retry_at <= now
        )
        if not is_pending and not is_retry_ready:
            return None
        delivery.status = Delivery.Status.PROCESSING
        delivery.next_retry_at = None
        delivery.processing_started_at = now
        delivery.processing_token = uuid.uuid4()
        delivery.save(
            update_fields = (
                "status",
                "next_retry_at",
                "processing_started_at",
                "processing_token",
                "updated_at",
            )
        )
    return delivery


def get_retry_delay(attempts):
    if attempts <= 0:
        return 30

    initial_delay = 30
    max_delay = 3600

    delay = initial_delay * (2 ** (attempts - 1))
    return min(delay, max_delay)

def is_retryable_status(status_code):
    allowed_http = {408, 425, 429, 500, 502, 503, 504}
    return status_code in allowed_http


def retry_delivery(delivery_id, user):
    with transaction.atomic():
        delivery = Delivery.objects.select_for_update().get(
            id=delivery_id,
            event__owner=user,
        )
        if delivery.status != Delivery.Status.FAILED:
            raise ValidationError("Delivery cannot be retried")
        delivery.status = Delivery.Status.PENDING
        delivery.next_retry_at = None
        delivery.save(
            update_fields=(
            "status",
            "next_retry_at",
            "updated_at"
        ))
        transaction.on_commit(
            lambda: send_delivery_task.delay(str(delivery.id))
        )

    return delivery

def recover_stuck_deliveries():
    stuck_before = timezone.now() - timedelta(minutes=5)

    with transaction.atomic():
        deliveries = (
            Delivery.objects
            .select_for_update()
            .filter(
                status=Delivery.Status.PROCESSING,
                processing_started_at__lt=stuck_before,
            )
        )

        recovered_count = deliveries.update(
            status=Delivery.Status.PENDING,
            processing_started_at=None,
            processing_token=None,
            updated_at=timezone.now(),
        )

    return recovered_count