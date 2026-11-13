from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from .models import Endpoint

User = get_user_model()


class EndpointAPITests(APITestCase):

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
            name="Main endpoint",
            url="https://example.com/webhook/",
        )

        self.other_endpoint = Endpoint.objects.create(
            owner=self.other_user,
            name="Other endpoint",
            url="https://other.com/webhook/",
        )

        self.list_url = reverse("endpoint-list")
        self.detail_url = reverse(
            "endpoint-detail",
            kwargs={"pk": self.endpoint.pk},
        )

        self.client.force_authenticate(user=self.user)

    def test_create_endpoint(self):
        response = self.client.post(
            self.list_url,
            {
                "name": "New endpoint",
                "url": "https://new.com/webhook/",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        endpoint = Endpoint.objects.get(name="New endpoint")

        self.assertEqual(endpoint.owner, self.user)
        self.assertTrue(endpoint.secret)
        self.assertNotIn("secret", response.data)

    def test_user_sees_only_own_endpoints(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            str(self.endpoint.pk),
        )

    def test_retrieve_own_endpoint(self):
        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_other_users_endpoint(self):
        url = reverse(
            "endpoint-detail",
            kwargs={"pk": self.other_endpoint.pk},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_other_users_endpoint(self):
        url = reverse(
            "endpoint-detail",
            kwargs={"pk": self.other_endpoint.pk},
        )

        response = self.client.patch(
            url,
            {"name": "Hacked"},
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_other_users_endpoint(self):
        url = reverse(
            "endpoint-detail",
            kwargs={"pk": self.other_endpoint.pk},
        )

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_user_cannot_access_endpoints(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(self.list_url)

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ]
        )

    def test_cannot_change_owner_through_request(self):
        response = self.client.post(
            self.list_url,
            {
                "name": "Attempted ownership change",
                "url": "https://evil.com/webhook/",
                "owner": self.other_user.pk,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        endpoint = Endpoint.objects.get(
            name="Attempted ownership change"
        )

        self.assertEqual(endpoint.owner, self.user)

    def test_endpoint_secrets_are_unique(self):
        endpoint = Endpoint.objects.create(
            owner=self.user,
            name="Another endpoint",
            url="https://another.com/webhook/",
        )

        self.assertNotEqual(
            self.endpoint.secret,
            endpoint.secret,
        )

    def test_secret_is_not_exposed_in_api_response(self):
        response = self.client.get(self.detail_url)

        self.assertNotIn("secret", response.data)
