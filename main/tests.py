from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Client, Invoice, InvoiceItem


class InvoiceTotalsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("owner", password="pw")
        self.invoice = Invoice.objects.create(user=self.user, vat_rate=15)

    def add_item(self, amount, quantity=1):
        item = InvoiceItem.objects.create(
            invoice=self.invoice, title="Item", amount=Decimal(amount), quantity=quantity
        )
        self.invoice.save()
        return item

    def test_vat_is_applied_with_decimal_math(self):
        self.add_item("100.00", quantity=2)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_amount, Decimal("200.00"))
        self.assertEqual(self.invoice.vat_rate_amount, Decimal("30.00"))
        self.assertEqual(self.invoice.total_amount_final, Decimal("230.00"))

    def test_vat_amount_is_rounded_to_cents(self):
        self.add_item("10.33")
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.vat_rate_amount, Decimal("1.55"))
        self.assertEqual(self.invoice.total_amount_final, Decimal("11.88"))

    def test_inactive_items_are_excluded_from_totals(self):
        self.add_item("100.00")
        removed = self.add_item("50.00")
        removed.is_active = False
        removed.save()
        self.invoice.save()
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_amount, Decimal("100.00"))
        self.assertEqual(self.invoice.total_amount_final, Decimal("115.00"))

    def test_totals_reset_when_all_items_removed(self):
        item = self.add_item("100.00")
        item.is_active = False
        item.save()
        self.invoice.save()
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_amount, Decimal("0"))
        self.assertEqual(self.invoice.vat_rate_amount, Decimal("0"))
        self.assertEqual(self.invoice.total_amount_final, Decimal("0"))

    def test_vat_amount_resets_when_rate_set_to_zero(self):
        self.add_item("100.00")
        self.invoice.vat_rate = 0
        self.invoice.save()
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.vat_rate_amount, Decimal("0"))
        self.assertEqual(self.invoice.total_amount_final, Decimal("100.00"))


class InvoiceApiTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw")
        self.other = User.objects.create_user("other", password="pw")
        self.client_record = Client.objects.create(
            name="Acme", email="acme@example.com", user=self.owner
        )
        self.invoice = Invoice.objects.create(
            user=self.owner, client=self.client_record, vat_rate=10
        )
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def test_create_invoice_with_vat_and_items(self):
        response = self.api.post(
            "/api/invoices/",
            {
                "client": self.client_record.id,
                "vat_rate": 20,
                "items": [{"title": "Design", "amount": "50.00", "quantity": 2}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        invoice = Invoice.objects.exclude(pk=self.invoice.pk).get()
        self.assertEqual(invoice.total_amount_final, Decimal("120.00"))

    def test_updating_items_replaces_old_items_in_total(self):
        InvoiceItem.objects.create(invoice=self.invoice, title="Old", amount=Decimal("100"))
        self.invoice.save()
        response = self.api.patch(
            f"/api/invoices/{self.invoice.id}/",
            {"items": [{"title": "New", "amount": "40.00", "quantity": 1}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_amount, Decimal("40.00"))
        self.assertEqual(self.invoice.total_amount_final, Decimal("44.00"))

    def test_soft_deleting_item_lowers_total(self):
        item = InvoiceItem.objects.create(invoice=self.invoice, title="A", amount=Decimal("100"))
        self.invoice.save()
        response = self.api.delete(f"/api/invoice-items/{item.id}/")
        self.assertEqual(response.status_code, 204)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_amount_final, Decimal("0"))

        response = self.api.post(f"/api/invoice-items/{item.id}/restore/")
        self.assertEqual(response.status_code, 200)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_amount_final, Decimal("110.00"))

    def test_cannot_add_item_to_another_users_invoice(self):
        self.api.force_authenticate(self.other)
        response = self.api.post(
            "/api/invoice-items/",
            {"invoice": self.invoice.id, "title": "Sneaky", "amount": "999.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("invoice", response.data)
        self.assertFalse(self.invoice.items.exists())

    def test_cannot_move_item_to_another_users_invoice(self):
        other_invoice = Invoice.objects.create(user=self.other)
        item = InvoiceItem.objects.create(invoice=self.invoice, title="A", amount=Decimal("10"))
        response = self.api.patch(
            f"/api/invoice-items/{item.id}/", {"invoice": other_invoice.id}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        item.refresh_from_db()
        self.assertEqual(item.invoice_id, self.invoice.id)

    def test_item_requires_an_invoice(self):
        response = self.api.post(
            "/api/invoice-items/", {"title": "Orphan", "amount": "5.00"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("invoice", response.data)

    def test_client_list_is_paginated(self):
        response = self.api.get("/api/clients/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["name"], "Acme")
