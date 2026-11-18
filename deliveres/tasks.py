from celery import shared_task
from datetime import timedelta

from .models import Delivery, OutboxMessage
from .services import send_delivery, claim_delivery, recover_stuck_deliveries
from django.utils import timezone
from django.db import transaction
from django.db.models import Q


@shared_task
def send_delivery_task(delivery_id):
    try:
        delivery = claim_delivery(delivery_id)
    except Delivery.DoesNotExist:
        return

    if delivery is None:
        return

    send_delivery(delivery)

@shared_task
def dispatch_due_retries():
    now = timezone.now()

    delivery_ids = Delivery.objects.filter(
        status=Delivery.Status.FAILED,
        next_retry_at__lte=now,
    ).values_list("id", flat=True)

    for delivery_id in delivery_ids.iterator():
        send_delivery_task.delay(str(delivery_id))

@shared_task
def recover_stuck_deliveries_task():
    delivery_ids = recover_stuck_deliveries()

    for delivery_id in delivery_ids:
        send_delivery_task.delay(str(delivery_id))

    return len(delivery_ids)


def enqueue_deliveries(delivery_ids):
    for delivery_id in delivery_ids:
        send_delivery_task.delay(str(delivery_id))


@shared_task
def dispatch_outbox_messages():
    now = timezone.now()
    deadline = now - timedelta(minutes=5)

    with transaction.atomic():
        outbox_messages = list(
            OutboxMessage.objects
            .select_for_update(skip_locked=True)
            .filter(
                processed_at__isnull=True,
            )
            .filter(
                Q(claimed_at__isnull=True)
                | Q(claimed_at__lt=deadline)
            )
            .order_by("created_at")[:100]
        )

        message_ids = [
            message.id for message in outbox_messages
        ]

        OutboxMessage.objects.filter(
            id__in=message_ids,
        ).update(claimed_at=now)

    published_count = 0

    for message in outbox_messages:
        try:
            send_delivery_task.delay(
                str(message.delivery_id)
            )
        except Exception:
            continue

        OutboxMessage.objects.filter(
            id=message.id,
            processed_at__isnull=True,
        ).update(
            processed_at=timezone.now(),
            claimed_at=None,
        )

        published_count += 1

    return published_count
