import re
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import BusinessProfile, Client, Invoice, InvoiceItem
from .pdf import build_invoice_pdf

PROFILE_URL = "/api/profile/"
PROFILE_FIELDS = {
    "business_name", "address", "email", "phone", "tax_id",
    "payment_instructions", "footer_note",
}
NASTY = "<b>&</b> <script>alert(1)</script> & co <i"


def uncompressed_pdf(invoice):
    """Render with stream compression off so content text can be searched."""
    with mock.patch("reportlab.rl_config.pageCompression", 0):
        return build_invoice_pdf(invoice)


def pdf_text(pdf):
    """Concatenate the text-showing strings of an uncompressed PDF.

    Strings are joined without a separator because ReportLab draws text
    around escaped characters (e.g. "<", "&") as separate fragments.
    """
    strings = re.findall(rb"\(((?:\\.|[^\\)])*)\)\s*Tj", pdf)
    text = b"".join(strings)
    return re.sub(rb"\\([()\\])", rb"\1", text).decode("latin-1")


def page_count(pdf):
    # Page objects are "/Type /Page"; the page tree root is "/Type /Pages".
    return len(re.findall(rb"/Type /Page(?![a-zA-Z])", pdf))


class BusinessProfileApiTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw")
        self.bob = User.objects.create_user("bob", password="pw")
        self.api = APIClient()
        self.api.force_authenticate(self.alice)

    def test_get_auto_creates_empty_profile(self):
        self.assertFalse(BusinessProfile.objects.filter(user=self.alice).exists())
        response = self.api.get(PROFILE_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), PROFILE_FIELDS)
        self.assertTrue(all(value == "" for value in response.data.values()))
        self.assertEqual(BusinessProfile.objects.filter(user=self.alice).count(), 1)
        # A second GET reuses the same row.
        self.api.get(PROFILE_URL)
        self.assertEqual(BusinessProfile.objects.filter(user=self.alice).count(), 1)

    def test_patch_updates_fields(self):
        response = self.api.patch(
            PROFILE_URL,
            {"business_name": "Alice Studio", "tax_id": "GB123", "address": "1 Road\nTown"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["business_name"], "Alice Studio")
        profile = BusinessProfile.objects.get(user=self.alice)
        self.assertEqual(profile.tax_id, "GB123")
        self.assertEqual(profile.address, "1 Road\nTown")
        self.assertEqual(profile.email, "")

    def test_put_replaces_profile(self):
        payload = {field: "" for field in PROFILE_FIELDS}
        payload.update(business_name="Full", email="billing@example.com")
        response = self.api.put(PROFILE_URL, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(BusinessProfile.objects.get(user=self.alice).email, "billing@example.com")

    def test_invalid_email_rejected(self):
        response = self.api.patch(PROFILE_URL, {"email": "not-an-email"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_cannot_reassign_profile_owner(self):
        self.api.patch(PROFILE_URL, {"user": self.bob.id, "business_name": "A"}, format="json")
        self.assertEqual(BusinessProfile.objects.get(business_name="A").user, self.alice)
        self.assertFalse(BusinessProfile.objects.filter(user=self.bob).exists())

    def test_users_only_see_their_own_profile(self):
        BusinessProfile.objects.create(user=self.alice, business_name="Alice Secret Co")
        bob_api = APIClient()
        bob_api.force_authenticate(self.bob)
        response = bob_api.get(PROFILE_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["business_name"], "")
        bob_api.patch(PROFILE_URL, {"business_name": "Bob Co"}, format="json")
        self.assertEqual(
            BusinessProfile.objects.get(user=self.alice).business_name, "Alice Secret Co"
        )

    def test_anonymous_is_rejected(self):
        anon = APIClient()
        self.assertIn(anon.get(PROFILE_URL).status_code, (401, 403))
        self.assertIn(
            anon.patch(PROFILE_URL, {"business_name": "x"}, format="json").status_code,
            (401, 403),
        )
        self.assertFalse(BusinessProfile.objects.exists())


class InvoicePdfTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("owner", password="pw", first_name="Olive", last_name="Owner")
        self.client_record = Client.objects.create(
            user=self.user, name="Acme Ltd", email="acme@example.com", phone="555-0100"
        )

    def make_invoice(self, items=0, client=True, vat_rate=0, **kwargs):
        invoice = Invoice.objects.create(
            user=self.user,
            client=self.client_record if client else None,
            vat_rate=vat_rate,
            **kwargs,
        )
        for i in range(items):
            InvoiceItem.objects.create(
                invoice=invoice, title=f"Item {i}", description=f"Description {i}",
                amount=Decimal("10.00"), quantity=2,
            )
        invoice.save()
        return invoice

    def test_pdf_basic(self):
        pdf = build_invoice_pdf(self.make_invoice(items=3))
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(page_count(pdf), 1)

    def test_no_client_and_no_items(self):
        invoice = self.make_invoice(items=0, client=False)
        pdf = uncompressed_pdf(invoice)
        self.assertTrue(pdf.startswith(b"%PDF"))
        text = pdf_text(pdf)
        self.assertIn("No items on this invoice.", text)
        self.assertIn("BILL TO", text)
        self.assertNotIn("None", text)

    def test_missing_optional_fields_do_not_render_none(self):
        invoice = self.make_invoice(client=False)
        InvoiceItem.objects.create(invoice=invoice, title=None, description=None, amount=Decimal("5.00"))
        InvoiceItem.objects.create(invoice=invoice, title="Only title", description=None, amount=Decimal("5.00"))
        InvoiceItem.objects.create(invoice=invoice, title=None, description="Only desc", amount=Decimal("5.00"))
        invoice.save()
        text = pdf_text(uncompressed_pdf(invoice))
        self.assertNotIn("None", text)
        self.assertIn("Only title", text)
        self.assertIn("Only desc", text)

    def test_many_items_paginate_with_page_x_of_y(self):
        invoice = self.make_invoice(items=200)
        pdf = uncompressed_pdf(invoice)
        pages = page_count(pdf)
        self.assertGreater(pages, 1)
        number = invoice.number.encode()
        for page in (1, pages):
            self.assertIn(f"Page {page} of {pages}".encode(), pdf)
        self.assertNotIn(f"Page {pages + 1} of".encode(), pdf)
        self.assertEqual(pdf.count(number + b" \\267 Page "), pages)
        # Header row is repeated on every page.
        self.assertEqual(pdf.count(b"(Unit price)"), pages)
        self.assertIn(b"Item 199", pdf)

    def test_business_details_and_number_appear(self):
        BusinessProfile.objects.create(
            user=self.user, business_name="Olive Design", address="1 Main St\nSpringfield",
            email="hi@olive.example", phone="555-9999", tax_id="VAT-42",
            payment_instructions="IBAN XX00 1234", footer_note="Thanks a lot",
        )
        invoice = self.make_invoice(items=2)
        pdf = uncompressed_pdf(invoice)
        for text in (
            b"Olive Design", b"1 Main St", b"Springfield", b"hi@olive.example",
            b"VAT-42", b"IBAN XX00 1234", b"Thanks a lot", b"Acme Ltd",
            invoice.number.encode(), b"Page 1 of 1", b"INVOICE",
        ):
            self.assertIn(text, pdf)

    def test_sender_falls_back_to_user_name_without_profile(self):
        pdf = uncompressed_pdf(self.make_invoice(items=1))
        self.assertIn(b"Olive Owner", pdf)
        self.user.first_name = self.user.last_name = ""
        self.user.save()
        pdf = uncompressed_pdf(self.make_invoice(items=1))
        self.assertIn(b"(owner)", pdf)

    def test_pdf_render_does_not_create_profile(self):
        build_invoice_pdf(self.make_invoice(items=1))
        self.assertFalse(BusinessProfile.objects.exists())

    def test_markup_in_user_text_is_escaped(self):
        BusinessProfile.objects.create(
            user=self.user, business_name=NASTY, address=NASTY, tax_id=NASTY,
            payment_instructions=NASTY, footer_note=NASTY,
        )
        self.client_record.name = NASTY
        self.client_record.phone = "<x>&"
        self.client_record.save()
        invoice = self.make_invoice()
        InvoiceItem.objects.create(
            invoice=invoice, title=NASTY, description=NASTY + "\nline two\x00\x07",
            amount=Decimal("1.00"),
        )
        invoice.save()
        pdf = uncompressed_pdf(invoice)
        self.assertTrue(pdf.startswith(b"%PDF"))
        # The literal tag text is drawn rather than interpreted as markup.
        text = pdf_text(pdf)
        self.assertIn("<b>&</b>", text)
        self.assertIn("<script>alert(1)</script>", text)
        self.assertIn("<x>&", text)
        self.assertIn("line two", text)

    def test_non_latin_text_does_not_crash(self):
        BusinessProfile.objects.create(user=self.user, business_name="Café € 日本 \U0001F600")
        invoice = self.make_invoice(items=1)
        self.assertTrue(build_invoice_pdf(invoice).startswith(b"%PDF"))

    def test_vat_line_only_when_rate_positive(self):
        no_vat = pdf_text(uncompressed_pdf(self.make_invoice(items=1, vat_rate=0)))
        self.assertNotIn("VAT (", no_vat)
        self.assertIn("Subtotal", no_vat)
        with_vat = pdf_text(uncompressed_pdf(self.make_invoice(items=1, vat_rate=20)))
        self.assertIn("VAT (20%)", with_vat)
        self.assertIn("$4.00", with_vat)  # 20% of $20.00
        self.assertIn("$24.00", with_vat)

    def test_paid_indicator(self):
        unpaid = pdf_text(uncompressed_pdf(self.make_invoice(items=1)))
        self.assertIn("Unpaid", unpaid)
        self.assertNotIn("PAID", unpaid)
        paid = pdf_text(uncompressed_pdf(self.make_invoice(items=1, status="paid")))
        self.assertIn("PAID", paid)

    def test_owner_download_endpoint_returns_pdf(self):
        invoice = self.make_invoice(items=2)
        api = APIClient()
        api.force_authenticate(self.user)
        response = api.get(f"/api/invoices/{invoice.id}/download_pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_public_share_link_pdf_returns_pdf(self):
        invoice = self.make_invoice(items=2)
        invoice.generate_share_link()
        response = APIClient().get(f"/api/public/invoices/{invoice.share_link_id}/pdf/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertFalse(BusinessProfile.objects.exists())
