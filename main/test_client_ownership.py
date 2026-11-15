import importlib
from datetime import timedelta

from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Client, Invoice

backfill_client_owners = importlib.import_module(
    "main.migrations.0013_client_user"
).backfill_client_owners


class ClientOwnershipApiTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw")
        self.other = User.objects.create_user("other", password="pw")
        self.own_client = Client.objects.create(
            name="Acme", email="acme@example.com", user=self.owner
        )
        self.foreign_client = Client.objects.create(
            name="Globex", email="globex@example.com", user=self.other
        )
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def test_list_only_shows_own_clients(self):
        response = self.api.get("/api/clients/")
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.data["results"]]
        self.assertEqual(ids, [self.own_client.id])

    def test_ownerless_clients_are_not_listed(self):
        Client.objects.create(name="Legacy", email="legacy@example.com")
        response = self.api.get("/api/clients/")
        names = [row["name"] for row in response.data["results"]]
        self.assertNotIn("Legacy", names)

    def test_cannot_retrieve_another_users_client(self):
        response = self.api.get(f"/api/clients/{self.foreign_client.id}/")
        self.assertEqual(response.status_code, 404)

    def test_cannot_update_another_users_client(self):
        response = self.api.patch(
            f"/api/clients/{self.foreign_client.id}/", {"name": "Hijacked"}, format="json"
        )
        self.assertEqual(response.status_code, 404)
        self.foreign_client.refresh_from_db()
        self.assertEqual(self.foreign_client.name, "Globex")

    def test_cannot_delete_another_users_client(self):
        response = self.api.delete(f"/api/clients/{self.foreign_client.id}/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Client.objects.filter(pk=self.foreign_client.pk).exists())

    def test_can_update_and_delete_own_client(self):
        response = self.api.patch(
            f"/api/clients/{self.own_client.id}/", {"name": "Acme Corp"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        response = self.api.delete(f"/api/clients/{self.own_client.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Client.objects.filter(pk=self.own_client.pk).exists())

    def test_create_assigns_request_user(self):
        response = self.api.post(
            "/api/clients/", {"name": "Initech", "email": "initech@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Client.objects.get(pk=response.data["id"]).user, self.owner)

    def test_create_ignores_user_in_payload(self):
        response = self.api.post(
            "/api/clients/",
            {"name": "Initech", "email": "initech@example.com", "user": self.other.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Client.objects.get(pk=response.data["id"]).user, self.owner)

    def test_cannot_create_invoice_with_another_users_client(self):
        response = self.api.post(
            "/api/invoices/", {"client": self.foreign_client.id, "vat_rate": 0}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("client", response.data)
        self.assertFalse(Invoice.objects.exists())

    def test_cannot_move_invoice_to_another_users_client(self):
        invoice = Invoice.objects.create(user=self.owner, client=self.own_client)
        response = self.api.patch(
            f"/api/invoices/{invoice.id}/", {"client": self.foreign_client.id}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        invoice.refresh_from_db()
        self.assertEqual(invoice.client_id, self.own_client.id)

    def test_can_create_invoice_with_own_or_no_client(self):
        response = self.api.post(
            "/api/invoices/", {"client": self.own_client.id, "vat_rate": 0}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        response = self.api.post(
            "/api/invoices/", {"client": None, "vat_rate": 0}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)


class ClientOwnerBackfillTests(TestCase):
    def test_backfill_uses_earliest_invoice_owner(self):
        first = User.objects.create_user("first", password="pw")
        second = User.objects.create_user("second", password="pw")
        shared = Client.objects.create(name="Shared", email="shared@example.com")
        later = Invoice.objects.create(user=second, client=shared)
        earlier = Invoice.objects.create(user=first, client=shared)
        # created_at is auto_now_add, so adjust ordering explicitly.
        now = timezone.now()
        Invoice.objects.filter(pk=earlier.pk).update(created_at=now - timedelta(days=2))
        Invoice.objects.filter(pk=later.pk).update(created_at=now - timedelta(days=1))
        uninvoiced = Client.objects.create(name="Lonely", email="lonely@example.com")
        already_owned = Client.objects.create(
            name="Owned", email="owned@example.com", user=second
        )
        Invoice.objects.create(user=first, client=already_owned)

        backfill_client_owners(apps, None)

        shared.refresh_from_db()
        uninvoiced.refresh_from_db()
        already_owned.refresh_from_db()
        self.assertEqual(shared.user, first)
        self.assertIsNone(uninvoiced.user)
        self.assertEqual(already_owned.user, second)


class LegacyClientInvoiceTests(TestCase):
    def test_invoice_can_keep_its_existing_ownerless_client(self):
        owner = User.objects.create_user("legacy", password="pw")
        legacy_client = Client.objects.create(name="Old Co", email="old@example.com")
        invoice = Invoice.objects.create(user=owner, client=legacy_client)
        api = APIClient()
        api.force_authenticate(owner)
        response = api.patch(
            f"/api/invoices/{invoice.id}/",
            {"client": legacy_client.id, "vat_rate": 5},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
