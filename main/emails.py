"""Outgoing email for invoices."""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from .models import BusinessProfile
from .pdf import build_invoice_pdf


def invoice_sender_name(invoice):
    """Name shown as the sender of an invoice (subject line and sign-off).

    Uses the business name from the user's profile, like the PDF header does,
    falling back to the account's full name or username.
    """
    user = invoice.user
    profile = BusinessProfile.for_user_readonly(user)
    return profile.business_name.strip() or user.get_full_name() or user.username


def invoice_share_url(invoice):
    """Public URL of the invoice's share page on the frontend."""
    return f"{settings.FRONTEND_URL}/share/{invoice.share_link_id}"


def send_invoice_email(invoice, *, message=""):
    """Email the invoice to its client, with the PDF attached.

    Generates a share link if the invoice has none. On success the invoice is
    marked as sent; if sending fails the exception propagates and the invoice
    is not marked as sent (a newly generated share link is kept).
    """
    if not invoice.share_link_id:
        invoice.generate_share_link()

    sender_name = invoice_sender_name(invoice)
    context = {
        "invoice": invoice,
        "client_name": invoice.client.name,
        "sender_name": sender_name,
        "message": message.strip(),
        "share_url": invoice_share_url(invoice),
    }
    reply_to = [invoice.user.email] if invoice.user.email else None

    email = EmailMultiAlternatives(
        subject=f"Invoice {invoice.number} from {sender_name}",
        body=render_to_string("main/emails/invoice.txt", context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[invoice.client.email],
        reply_to=reply_to,
    )
    email.attach_alternative(
        render_to_string("main/emails/invoice.html", context), "text/html"
    )
    email.attach(
        f"{invoice.number}.pdf", build_invoice_pdf(invoice), "application/pdf"
    )
    email.send()

    invoice.sent = "sent"
    invoice.sent_at = timezone.now()
    invoice.save()
    return invoice
