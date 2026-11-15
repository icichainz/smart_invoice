import datetime
import smtplib
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .emails import invoice_sender_name
from .models import BusinessProfile, Client, Invoice, InvoiceItem


LOCMEM_SEND = "django.core.mail.backends.locmem.EmailBackend.send_messages"


@override_settings(
    FRONTEND_URL="https://app.example.com",
    DEFAULT_FROM_EMAIL="Smart Invoice <noreply@example.com>",
)
class SendInvoiceEmailTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            "owner", email="owner@example.com", password="pw",
            first_name="Ada", last_name="Lovelace",
        )
        self.client_record = Client.objects.create(
            user=self.owner, name="Acme", email="billing@acme.example"
        )
        self.invoice = Invoice.objects.create(
            user=self.owner, client=self.client_record, vat_rate=10,
            due_date=datetime.date(2026, 12, 31),
        )
        InvoiceItem.objects.create(
            invoice=self.invoice, title="Design", description="Logo design",
            amount=Decimal("100.00"), quantity=2,
        )
        self.invoice.save()
        self.invoice.refresh_from_db()

        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def url(self, invoice=None):
        return f"/api/invoices/{(invoice or self.invoice).id}/send_email/"

    def send(self, data=None, invoice=None):
        return self.api.post(self.url(invoice), data or {}, format="json")

    def html_body(self, message):
        self.assertEqual(len(message.alternatives), 1)
        content, mimetype = message.alternatives[0]
        self.assertEqual(mimetype, "text/html")
        return content

    # --- Happy path -------------------------------------------------------

    def test_sends_email_to_client(self):
        response = self.send()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "success")
        self.assertIn("billing@acme.example", response.data["message"])
        self.assertEqual(len(mail.outbox), 1)

        message = mail.outbox[0]
        self.invoice.refresh_from_db()
        share_url = f"https://app.example.com/share/{self.invoice.share_link_id}"

        self.assertEqual(message.to, ["billing@acme.example"])
        self.assertEqual(message.from_email, "Smart Invoice <noreply@example.com>")
        self.assertEqual(message.reply_to, ["owner@example.com"])
        self.assertEqual(
            message.subject, f"Invoice {self.invoice.number} from Ada Lovelace"
        )
        self.assertIn("Hello Acme,", message.body)
        self.assertIn(self.invoice.number, message.body)
        self.assertIn("$220.00", message.body)
        self.assertIn("December 31, 2026", message.body)
        self.assertIn(share_url, message.body)
        self.assertIn("Ada Lovelace", message.body)

        html = self.html_body(message)
        self.assertIn(share_url, html)
        self.assertIn("$220.00", html)

    def test_attaches_pdf(self):
        self.send()

        attachments = mail.outbox[0].attachments
        self.assertEqual(len(attachments), 1)
        filename, content, mimetype = attachments[0]
        self.assertEqual(filename, f"{self.invoice.number}.pdf")
        self.assertEqual(mimetype, "application/pdf")
        self.assertTrue(content.startswith(b"%PDF"))

    def test_marks_invoice_as_sent(self):
        self.assertEqual(self.invoice.sent, "not sent")
        self.assertIsNone(self.invoice.sent_at)

        response = self.send()

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.sent, "sent")
        self.assertIsNotNone(self.invoice.sent_at)
        self.assertEqual(response.data["data"]["sent"], "sent")
        self.assertIsNotNone(response.data["data"]["sent_at"])

    def test_generates_share_link_when_missing(self):
        self.assertIsNone(self.invoice.share_link_id)

        response = self.send()

        self.invoice.refresh_from_db()
        self.assertIsNotNone(self.invoice.share_link_id)
        self.assertEqual(
            response.data["data"]["share_link_id"], str(self.invoice.share_link_id)
        )

    def test_reuses_existing_share_link(self):
        self.invoice.generate_share_link()
        existing = self.invoice.share_link_id

        self.send()

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.share_link_id, existing)
        self.assertIn(f"/share/{existing}", mail.outbox[0].body)

    def test_custom_message_included(self):
        response = self.send({"message": "Thanks for the great project!"})

        self.assertEqual(response.status_code, 200)
        message = mail.outbox[0]
        self.assertIn("Thanks for the great project!", message.body)
        self.assertIn("Thanks for the great project!", self.html_body(message))

    def test_html_escapes_user_content(self):
        self.client_record.name = "<script>alert(1)</script>"
        self.client_record.save()

        self.send({"message": "<b>hi</b>"})

        message = mail.outbox[0]
        html = self.html_body(message)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<b>hi</b>", html)
        self.assertIn("&lt;b&gt;hi&lt;/b&gt;", html)
        # The plain-text part is not HTML, so it carries the text verbatim.
        self.assertIn("Hello <script>alert(1)</script>,", message.body)

    def test_no_reply_to_when_user_has_no_email(self):
        self.owner.email = ""
        self.owner.save()

        self.send()

        self.assertEqual(mail.outbox[0].reply_to, [])

    def test_sender_name_falls_back_to_username(self):
        self.owner.first_name = ""
        self.owner.last_name = ""
        self.owner.save()
        self.invoice.refresh_from_db()

        self.assertEqual(invoice_sender_name(self.invoice), "owner")
        self.send()
        self.assertEqual(
            mail.outbox[0].subject, f"Invoice {self.invoice.number} from owner"
        )

    # --- Validation -------------------------------------------------------

    def assert_rejected(self, response, fragment):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["status"], "error")
        self.assertIn(fragment, response.data["message"])
        self.assertEqual(len(mail.outbox), 0)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.sent, "not sent")
        self.assertIsNone(self.invoice.sent_at)

    def test_rejects_draft(self):
        self.invoice.save_as_draft = True
        self.invoice.save()
        self.assert_rejected(self.send(), "Draft")

    def test_rejects_invoice_without_client(self):
        self.invoice.client = None
        self.invoice.save()
        self.assert_rejected(self.send(), "client")

    def test_rejects_client_without_email(self):
        self.client_record.email = ""
        self.client_record.save()
        self.assert_rejected(self.send(), "no email")

    def test_rejects_invoice_without_active_items(self):
        self.invoice.items.update(is_active=False)
        self.assert_rejected(self.send(), "item")

    def test_rejects_overlong_message(self):
        response = self.send({"message": "x" * 2001})
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.data)
        self.assertEqual(len(mail.outbox), 0)

    # --- Access control ---------------------------------------------------

    def test_other_user_gets_404(self):
        intruder = User.objects.create_user("intruder", password="pw")
        api = APIClient()
        api.force_authenticate(intruder)

        response = api.post(self.url(), {}, format="json")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(mail.outbox), 0)

    def test_anonymous_rejected(self):
        response = APIClient().post(self.url(), {}, format="json")
        self.assertIn(response.status_code, (401, 403))
        self.assertEqual(len(mail.outbox), 0)

    # --- Delivery failure -------------------------------------------------

    def test_mail_server_failure_returns_502_and_does_not_mark_sent(self):
        errors = [
            smtplib.SMTPException("boom"),
            ConnectionRefusedError("refused"),
        ]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                with mock.patch(LOCMEM_SEND, side_effect=error), \
                        self.assertLogs("main.api_views", level="ERROR"):
                    response = self.send()

                self.assertEqual(response.status_code, 502)
                self.assertEqual(response.data, {
                    "status": "error",
                    "message": "Could not send the email. Check the mail server settings.",
                })
                self.invoice.refresh_from_db()
                self.assertEqual(self.invoice.sent, "not sent")
                self.assertIsNone(self.invoice.sent_at)
                self.assertEqual(len(mail.outbox), 0)

    def test_unknown_invoice_returns_404(self):
        response = self.api.post("/api/invoices/999999/send_email/", {}, format="json")
        self.assertEqual(response.status_code, 404)


class InvoiceSenderNameTests(TestCase):
    def test_business_name_is_used_when_profile_has_one(self):
        user = User.objects.create_user("dana", password="pw", first_name="Dana", last_name="Lee")
        invoice = Invoice.objects.create(user=user)
        self.assertEqual(invoice_sender_name(invoice), "Dana Lee")

        BusinessProfile.objects.create(user=user, business_name="Lee Studio")
        self.assertEqual(invoice_sender_name(invoice), "Lee Studio")
