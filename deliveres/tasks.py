from celery import shared_task

from .models import Delivery
from .services import send_delivery, claim_delivery


def enqueue_deliveries(delivery_ids):
    for delivery_id in delivery_ids:
        send_delivery_task.delay(delivery_id)


@shared_task
def send_delivery_task(delivery_id):
    try:
        delivery = claim_delivery(delivery_id)
    except Delivery.DoesNotExist:
        return

    if delivery is None:
        return

    send_delivery(delivery)