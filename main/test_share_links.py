import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Client, Invoice, InvoiceItem


class ShareLinkTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw")
        self.client_record = Client.objects.create(name="Acme", email="acme@example.com")
        self.invoice = Invoice.objects.create(
            user=self.owner, client=self.client_record, vat_rate=10
        )
        self.active_item = InvoiceItem.objects.create(
            invoice=self.invoice, title="Design", description="Logo design",
            amount=Decimal("100.00"), quantity=2
        )
        self.inactive_item = InvoiceItem.objects.create(
            invoice=self.invoice, title="Removed", description="Secret line",
            amount=Decimal("999.00"), quantity=1, is_active=False
        )
        self.invoice.generate_share_link()
        self.invoice.refresh_from_db()

        self.owner_api = APIClient()
        self.owner_api.force_authenticate(self.owner)
        self.anon = APIClient()

    def public_url(self, share_id):
        return f"/api/public/invoices/{share_id}/"

    def public_pdf_url(self, share_id):
        return f"/api/public/invoices/{share_id}/pdf/"

    def test_anonymous_can_fetch_invoice_json(self):
        response = self.anon.get(self.public_url(self.invoice.share_link_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.invoice.id)
        self.assertEqual(response.data["client_name"], "Acme")
        self.assertEqual(response.data["client_email"], "acme@example.com")
        self.assertEqual(Decimal(response.data["total_amount"]), Decimal("200.00"))
        self.assertEqual(Decimal(response.data["vat_rate_amount"]), Decimal("20.00"))
        self.assertEqual(Decimal(response.data["total_amount_final"]), Decimal("220.00"))

    def test_anonymous_can_fetch_invoice_pdf(self):
        response = self.anon.get(self.public_pdf_url(self.invoice.share_link_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_unknown_share_id_returns_404(self):
        unknown = uuid.uuid4()
        self.assertEqual(self.anon.get(self.public_url(unknown)).status_code, 404)
        self.assertEqual(self.anon.get(self.public_pdf_url(unknown)).status_code, 404)

    def test_draft_invoice_is_not_served_publicly(self):
        self.invoice.save_as_draft = True
        self.invoice.save()
        share_id = self.invoice.share_link_id
        self.assertEqual(self.anon.get(self.public_url(share_id)).status_code, 404)
        self.assertEqual(self.anon.get(self.public_pdf_url(share_id)).status_code, 404)

    def test_public_response_hides_internal_fields_and_inactive_items(self):
        response = self.anon.get(self.public_url(self.invoice.share_link_id))
        self.assertEqual(response.status_code, 200)
        for field in ["user", "user_name", "share_link_id", "save_as_draft", "sent", "is_closed"]:
            self.assertNotIn(field, response.data)
        titles = [item["title"] for item in response.data["items"]]
        self.assertEqual(titles, ["Design"])
        self.assertNotIn("Secret line", str(response.content))
        self.assertNotIn("is_active", response.data["items"][0])
        self.assertNotIn("id", response.data["items"][0])

    def test_revoke_makes_link_404(self):
        share_id = self.invoice.share_link_id
        response = self.owner_api.post(f"/api/invoices/{self.invoice.id}/revoke_share_link/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["data"]["share_link_id"])
        self.invoice.refresh_from_db()
        self.assertIsNone(self.invoice.share_link_id)
        self.assertEqual(self.anon.get(self.public_url(share_id)).status_code, 404)
        self.assertEqual(self.anon.get(self.public_pdf_url(share_id)).status_code, 404)

    def test_revoke_requires_owner(self):
        other = User.objects.create_user("other", password="pw")
        other_api = APIClient()
        other_api.force_authenticate(other)
        response = other_api.post(f"/api/invoices/{self.invoice.id}/revoke_share_link/")
        self.assertEqual(response.status_code, 404)
        response = self.anon.post(f"/api/invoices/{self.invoice.id}/revoke_share_link/")
        self.assertIn(response.status_code, (401, 403))
        self.invoice.refresh_from_db()
        self.assertIsNotNone(self.invoice.share_link_id)

    def test_regenerate_gives_new_id_and_old_one_404s(self):
        old_id = self.invoice.share_link_id
        response = self.owner_api.post(f"/api/invoices/{self.invoice.id}/generate_share_link/")
        self.assertEqual(response.status_code, 200)
        new_id = response.data["data"]["share_link_id"]
        self.assertIsNotNone(new_id)
        self.assertNotEqual(str(new_id), str(old_id))
        self.assertEqual(self.anon.get(self.public_url(old_id)).status_code, 404)
        self.assertEqual(self.anon.get(self.public_url(new_id)).status_code, 200)

    def test_owner_download_pdf_still_works(self):
        response = self.owner_api.get(f"/api/invoices/{self.invoice.id}/download_pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(
            response["Content-Disposition"],
            f'attachment; filename="{self.invoice.number}.pdf"',
        )
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_anonymous_cannot_download_pdf_by_pk(self):
        response = self.anon.get(f"/api/invoices/{self.invoice.id}/download_pdf/")
        self.assertIn(response.status_code, (401, 403))
