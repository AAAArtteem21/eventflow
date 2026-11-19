from .models import Delivery, OutboxMessage, DeliveryAttempt
from endpoints.models import Endpoint
import httpx
import uuid
import json
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
import hashlib
import hmac
from endpoints.validators import validate_endpoint_url

MAX_ATTEMPTS = 8

@transaction.atomic
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

    created =  Delivery.objects.bulk_create(deliveries)
    outbox_messages = [OutboxMessage(delivery=delivery) for delivery in created]

    OutboxMessage.objects.bulk_create(outbox_messages)

def send_delivery(delivery: Delivery) -> bool:
    processing_token = delivery.processing_token

    if processing_token is None:
        return False

    with transaction.atomic():
        current = (
            Delivery.objects.select_for_update()
            .get(id=delivery.id)
        )

        if (
            current.status != Delivery.Status.PROCESSING
            or current.processing_token != processing_token
        ):
            return False

        current.attempts += 1
        attempt_number = current.attempts

        current.save(update_fields=["attempts", "updated_at"])

        attempt = DeliveryAttempt.objects.create(
            delivery=current,
            attempt_number=attempt_number,
        )

    event = delivery.event

    body = {
        "id": str(event.id),
        "event_type": event.event_type,
        "payload": event.payload,
        "created_at": event.created_at.isoformat(),
    }

    payload_bytes = json.dumps(
        body,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    signature = generate_signature(
        delivery.endpoint.secret,
        payload_bytes,
    )

    headers = {
        "Content-Type": "application/json",
        "X-EventFlow-Signature": signature,
        "X-EventFlow-Delivery": str(delivery.id),
    }

    response_status = None
    response_body = ""
    error = None
    retryable = False

    try:
        validate_endpoint_url(delivery.endpoint.url)

        with httpx.Client(
            timeout=10.0,
            follow_redirects=False,
        ) as client:
            response = client.post(
                delivery.endpoint.url,
                content=payload_bytes,
                headers=headers,
            )

        response_status = response.status_code
        response_body = response.text[:5000]

        if response.is_success:
            status = Delivery.Status.SUCCESS
        else:
            status = Delivery.Status.FAILED
            retryable = is_retryable_status(response_status)
            error = f"HTTP {response_status}"

    except ValidationError:
        status = Delivery.Status.FAILED
        retryable = False
        error = "Endpoint URL rejected by SSRF validation"

    except httpx.TimeoutException:
        status = Delivery.Status.FAILED
        retryable = True
        error = "Request timed out"

    except httpx.RequestError as exc:
        status = Delivery.Status.FAILED
        retryable = True
        error = f"Request error: {type(exc).__name__}"

    next_retry_at = None

    if retryable and attempt_number < MAX_ATTEMPTS:
        delay = get_retry_delay(attempt_number)
        next_retry_at = timezone.now() + timedelta(seconds=delay)

    with transaction.atomic():
        current = (
            Delivery.objects.select_for_update()
            .get(id=delivery.id)
        )

        attempt.response_status = response_status
        attempt.response_body = response_body
        attempt.error = error or ""
        attempt.finished_at = timezone.now()

        attempt.save(
            update_fields=[
                "response_status",
                "response_body",
                "error",
                "finished_at",
            ]
        )

        if (
            current.status != Delivery.Status.PROCESSING
            or current.processing_token != processing_token
        ):
            return False

        current.status = status
        current.last_response_status = response_status
        current.last_error = error or ""
        current.next_retry_at = next_retry_at
        current.processing_started_at = None
        current.processing_token = None

        current.save(
            update_fields=[
                "status",
                "last_response_status",
                "last_error",
                "next_retry_at",
                "processing_started_at",
                "processing_token",
                "updated_at",
            ]
        )

    return True

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

def save_delivery_result(delivery_id, processing_token, status, response_status=None):
    with transaction.atomic():
        delivery = Delivery.objects.select_for_update().get(id=delivery_id)
        if delivery.status != Delivery.Status.PROCESSING:
            return False 
        elif delivery.processing_token != processing_token:
            return False
        delivery.status = status
        delivery.last_response_status = response_status
        delivery.processing_started_at = None
        delivery.processing_token = None

        delivery.save(update_fields=[
            "status",
            "last_response_status",
            "processing_started_at",
            "processing_token",
        ])

    return True


def generate_signature(secret, payload):
    return "sha256=" + hmac.new(
        key=secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()
