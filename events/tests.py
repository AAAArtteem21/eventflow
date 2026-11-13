from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from .models import Event

User = get_user_model()


class EventAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="user1",
            password="password123",
        )

        self.other_user = User.objects.create_user(
            username="user2",
            password="password123",
        )

        self.client.force_authenticate(user=self.user)

        self.list_url = reverse("event-list")

        self.event = Event.objects.create(
            owner=self.user,
            event_type="payment.completed",
            payload={"payment_id": 123, "amount": 1500},
            idempotency_key="payment-123",
        )

        self.other_event = Event.objects.create(
            owner=self.other_user,
            event_type="payment.failed",
            payload={"payment_id": 456},
            idempotency_key="payment-456",
        )

    def test_create_event(self):
        response = self.client.post(
            self.list_url,
            {
                "event_type": "payment.completed",
                "payload": {
                    "payment_id": 789,
                    "amount": 2000,
                },
                "idempotency_key": "payment-789",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        event = Event.objects.get(
            idempotency_key="payment-789",
            owner=self.user,
        )

        self.assertEqual(event.owner, self.user)
        self.assertEqual(event.event_type, "payment.completed")
        self.assertEqual(event.payload["amount"], 2000)

    def test_create_event_with_owner_spoofing(self):
        response = self.client.post(
            self.list_url,
            {
                "event_type": "payment.completed",
                "payload": {},
                "idempotency_key": "spoof-123",
                "owner": self.other_user.pk,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        event = Event.objects.get(idempotency_key="spoof-123")

        self.assertEqual(event.owner, self.user)

    def test_duplicate_idempotency_key_returns_409(self):
        response = self.client.post(
            self.list_url,
            {
                "event_type": "payment.completed",
                "payload": {"payment_id": 999},
                "idempotency_key": "payment-123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )

    def test_duplicate_does_not_create_second_event(self):
        initial_count = Event.objects.filter(owner=self.user).count()

        self.client.post(
            self.list_url,
            {
                "event_type": "payment.completed",
                "payload": {},
                "idempotency_key": "payment-123",
            },
            format="json",
        )

        final_count = Event.objects.filter(owner=self.user).count()

        self.assertEqual(initial_count, final_count)

    def test_same_key_allowed_for_different_users(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            self.list_url,
            {
                "event_type": "payment.completed",
                "payload": {"payment_id": 777},
                "idempotency_key": "payment-123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_user_sees_only_own_events(self):
        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 1)

        self.assertEqual(
            response.data[0]["id"],
            str(self.event.pk),
        )

    def test_retrieve_own_event(self):
        url = reverse(
            "event-detail",
            kwargs={"pk": self.event.pk},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

    def test_cannot_retrieve_other_users_event(self):
        url = reverse(
            "event-detail",
            kwargs={"pk": self.other_event.pk},
        )

        response = self.client.get(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_unauthenticated_user_cannot_access_events(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

    def test_unauthenticated_user_cannot_create_event(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.list_url,
            {
                "event_type": "payment.completed",
                "payload": {},
                "idempotency_key": "anonymous-123",
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )

    def test_event_requires_event_type(self):
        response = self.client.post(
            self.list_url,
            {
                "payload": {},
                "idempotency_key": "missing-type",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_event_requires_idempotency_key(self):
        response = self.client.post(
            self.list_url,
            {
                "event_type": "payment.completed",
                "payload": {},
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_secret_or_owner_not_exposed(self):
        response = self.client.get(
            reverse(
                "event-detail",
                kwargs={"pk": self.event.pk},
            )
        )

        self.assertNotIn("owner", response.data)
        self.assertNotIn("secret", response.data)

    def test_cannot_update_event(self):
        url = reverse(
            "event-detail",
            kwargs={"pk": self.event.pk},
        )

        response = self.client.patch(
            url,
            {"event_type": "payment.failed"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_cannot_delete_event(self):
        url = reverse(
            "event-detail",
            kwargs={"pk": self.event.pk},
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
