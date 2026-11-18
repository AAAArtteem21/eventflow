from celery import shared_task
from datetime import timedelta

from .models import Delivery
from .services import send_delivery, claim_delivery, recover_stuck_deliveries
from django.utils import timezone
from django.db import transaction



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
