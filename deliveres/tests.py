from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from endpoints.models import Endpoint
from events.models import Event
from .models import Delivery, DeliveryAttempt


User = get_user_model()


class DeliveryAttemptAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="user1",
            password="password123",
        )

        self.other_user = User.objects.create_user(
            username="user2",
            password="password123",
        )

        self.endpoint = Endpoint.objects.create(
            owner=self.user,
            name="My endpoint",
            url="https://example.com/webhook",
            subscribed_events=["payment.completed"],
        )

        self.other_endpoint = Endpoint.objects.create(
            owner=self.other_user,
            name="Other endpoint",
            url="https://example.org/webhook",
            subscribed_events=["payment.completed"],
        )

        self.event = Event.objects.create(
            owner=self.user,
            event_type="payment.completed",
            payload={"amount": 100},
            idempotency_key="event-1",
        )

        self.other_event = Event.objects.create(
            owner=self.other_user,
            event_type="payment.completed",
            payload={"amount": 200},
            idempotency_key="event-2",
        )

        self.delivery = Delivery.objects.create(
            event=self.event,
            endpoint=self.endpoint,
        )

        self.other_delivery = Delivery.objects.create(
            event=self.other_event,
            endpoint=self.other_endpoint,
        )

        self.attempt = DeliveryAttempt.objects.create(
            delivery=self.delivery,
            attempt_number=1,
            response_status=500,
            response_body="Internal Server Error",
        )

        self.second_attempt = DeliveryAttempt.objects.create(
            delivery=self.delivery,
            attempt_number=2,
            response_status=200,
            response_body="OK",
        )

        self.other_attempt = DeliveryAttempt.objects.create(
            delivery=self.other_delivery,
            attempt_number=1,
            response_status=200,
            response_body="OK",
        )

        self.list_url = reverse("delivery-attempt-list")

    def test_authenticated_user_can_list_attempts(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 2)

    def test_user_sees_only_own_attempts(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.list_url)

        attempt_ids = {
            item["id"] for item in response.data
        }

        self.assertIn(str(self.attempt.id), attempt_ids)
        self.assertIn(str(self.second_attempt.id), attempt_ids)
        self.assertNotIn(str(self.other_attempt.id), attempt_ids)

    def test_filter_by_own_delivery_id(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            self.list_url,
            {"delivery_id": str(self.delivery.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_filter_by_foreign_delivery_id_returns_empty_list(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            self.list_url,
            {"delivery_id": str(self.other_delivery.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_user_can_retrieve_own_attempt(self):
        self.client.force_authenticate(user=self.user)

        url = reverse(
            "delivery-attempt-detail",
            kwargs={"pk": self.attempt.id},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["attempt_number"], 1)

    def test_user_cannot_retrieve_foreign_attempt(self):
        self.client.force_authenticate(user=self.user)

        url = reverse(
            "delivery-attempt-detail",
            kwargs={"pk": self.other_attempt.id},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_anonymous_user_cannot_list_attempts(self):
        response = self.client.get(self.list_url)

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

    def test_post_is_not_allowed(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(self.list_url, {})

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_attempts_are_ordered_by_attempt_number(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            self.list_url,
            {"delivery_id": str(self.delivery.id)},
        )

        numbers = [
            item["attempt_number"]
            for item in response.data
        ]

        self.assertEqual(numbers, [1, 2])