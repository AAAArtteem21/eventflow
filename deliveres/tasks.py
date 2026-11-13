from celery import shared_task

from .models import Delivery
from .services import send_delivery


@shared_task
def send_delivery_task(delivery_id):
    try:
        delivery = Delivery.objects.select_related(
            "event",
            "endpoint",
        ).get(id=delivery_id)
    except Delivery.DoesNotExist:
        return

    send_delivery(delivery)
