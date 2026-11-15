import importlib
from datetime import datetime, timezone as dt_timezone
from unittest import mock

from django.apps import apps
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Client, Invoice

backfill_invoice_numbers = importlib.import_module(
    "main.migrations.0014_invoice_number"
).backfill_invoice_numbers


def frozen_now(year):
    return mock.patch(
        "main.models.timezone.now",
        return_value=datetime(year, 6, 1, tzinfo=dt_timezone.utc),
    )


class InvoiceNumberTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw")
        self.bob = User.objects.create_user("bob", password="pw")

    def test_numbers_are_sequential_per_user(self):
        with frozen_now(2026):
            a1 = Invoice.objects.create(user=self.alice)
            a2 = Invoice.objects.create(user=self.alice)
            b1 = Invoice.objects.create(user=self.bob)
        self.assertEqual(a1.number, "INV-2026-0001")
        self.assertEqual(a2.number, "INV-2026-0002")
        self.assertEqual(b1.number, "INV-2026-0001")

    def test_sequence_restarts_each_year(self):
        with frozen_now(2026):
            Invoice.objects.create(user=self.alice)
            Invoice.objects.create(user=self.alice)
        with frozen_now(2027):
            first_of_year = Invoice.objects.create(user=self.alice)
        self.assertEqual(first_of_year.number, "INV-2027-0001")

    def test_number_is_stable_across_saves(self):
        invoice = Invoice.objects.create(user=self.alice)
        number = invoice.number
        invoice.vat_rate = 10
        invoice.save()
        invoice.refresh_from_db()
        self.assertEqual(invoice.number, number)

    def test_ordering_survives_more_than_9999_invoices(self):
        with frozen_now(2026):
            Invoice.objects.create(user=self.alice)
            Invoice.objects.filter(user=self.alice).update(
                sequence=9999, number="INV-2026-9999"
            )
            nxt = Invoice.objects.create(user=self.alice)
        self.assertEqual(nxt.number, "INV-2026-10000")

    def test_collision_retries_with_next_number(self):
        with frozen_now(2026):
            Invoice.objects.create(user=self.alice)
            original = Invoice._assign_number
            calls = []

            def stale_then_real(invoice):
                # First attempt behaves as if another request had not yet
                # committed INV-2026-0001; the retry must move past it.
                if not calls:
                    calls.append(1)
                    invoice.sequence = 1
                    invoice.number = "INV-2026-0001"
                    return
                original(invoice)

            with mock.patch.object(Invoice, "_assign_number", stale_then_real):
                second = Invoice.objects.create(user=self.alice)
        self.assertEqual(second.number, "INV-2026-0002")

    def test_api_exposes_number_read_only_and_searchable(self):
        api = APIClient()
        api.force_authenticate(self.alice)
        client = Client.objects.create(name="Acme", email="a@example.com", user=self.alice)
        response = api.post(
            "/api/invoices/", {"client": client.id, "number": "HACKED"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        invoice = Invoice.objects.get(user=self.alice)
        self.assertTrue(invoice.number.startswith("INV-"))

        listing = api.get("/api/invoices/", {"search": invoice.number})
        self.assertEqual([row["number"] for row in listing.data["results"]], [invoice.number])

    def test_copied_invoice_gets_new_number(self):
        api = APIClient()
        api.force_authenticate(self.alice)
        original = Invoice.objects.create(user=self.alice)
        response = api.post(f"/api/invoices/{original.id}/copy/")
        self.assertNotEqual(response.data["data"]["number"], original.number)

    def test_backfill_numbers_existing_invoices_in_creation_order(self):
        older = Invoice.objects.create(user=self.alice)
        newer = Invoice.objects.create(user=self.alice)
        other = Invoice.objects.create(user=self.bob)
        Invoice.objects.update(number="", sequence=None)
        Invoice.objects.filter(pk=older.pk).update(
            created_at=datetime(2025, 3, 1, tzinfo=dt_timezone.utc)
        )
        Invoice.objects.filter(pk=newer.pk).update(
            created_at=datetime(2025, 4, 1, tzinfo=dt_timezone.utc)
        )
        Invoice.objects.filter(pk=other.pk).update(
            created_at=datetime(2025, 5, 1, tzinfo=dt_timezone.utc)
        )

        backfill_invoice_numbers(apps, None)

        numbers = dict(Invoice.objects.values_list("pk", "number"))
        self.assertEqual(numbers[older.pk], "INV-2025-0001")
        self.assertEqual(numbers[newer.pk], "INV-2025-0002")
        self.assertEqual(numbers[other.pk], "INV-2025-0001")


class ClientPageSizeTests(TestCase):
    def test_page_size_param_is_capped(self):
        user = User.objects.create_user("carol", password="pw")
        Client.objects.bulk_create(
            Client(name=f"C{i:03d}", email=f"c{i}@example.com", user=user) for i in range(120)
        )
        api = APIClient()
        api.force_authenticate(user)
        self.assertEqual(len(api.get("/api/clients/").data["results"]), 20)
        self.assertEqual(len(api.get("/api/clients/", {"page_size": 50}).data["results"]), 50)
        self.assertEqual(len(api.get("/api/clients/", {"page_size": 500}).data["results"]), 100)
