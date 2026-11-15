import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.db import IntegrityError, models, transaction
from django.db.models import Max, Q
from django.contrib.auth.models import User
from django.utils import timezone


class Client(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="clients",
        null=True,
    )
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.name


class Invoice(models.Model):
    STATUS_CHOICES = (
        ("unpaid", "Unpaid"),
        ("paid", "Paid"),
    )
    EMAIL_CHOICES = (
        ("sent", "Sent"),
        ("not sent", "Not Sent"),
    )
    is_closed = models.BooleanField(
        default=False,
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        null=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    due_date = models.DateField(
        null=True,
    )
    vat_rate = models.IntegerField(
        default=0,
    )
    total_amount_final = models.DecimalField(
        max_digits=22,
        decimal_places=2,
        default=0,
    )
    total_amount = models.DecimalField(
        max_digits=22,
        decimal_places=2,
        default=0,
    )
    vat_rate_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="unpaid",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    save_as_draft = models.BooleanField(
        default=False,
    )
    share_link_id = models.UUIDField(
        null=True,
        blank=True,
    )
    sent = models.CharField(
        max_length=10,
        choices=EMAIL_CHOICES,
        default="not sent",
    )
    # When the invoice was last emailed to the client (see main/emails.py).
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )
    # Human-facing invoice number, e.g. "INV-2026-0001". Sequential per user
    # and per calendar year; assigned automatically on first save.
    number = models.CharField(
        max_length=32,
        blank=True,
        editable=False,
    )
    sequence = models.PositiveIntegerField(
        null=True,
        editable=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "number"],
                condition=~Q(number=""),
                name="unique_invoice_number_per_user",
            ),
        ]

    def __str__(self):
        return self.number or f"Invoice {self.pk}"

    def _assign_number(self):
        """Pick the next free number in this user's sequence for the year."""
        year = (self.created_at or timezone.now()).year
        prefix = f"INV-{year}-"
        last = (
            Invoice.objects.filter(user_id=self.user_id, number__startswith=prefix)
            .aggregate(last=Max("sequence"))["last"]
            or 0
        )
        self.sequence = last + 1
        self.number = f"{prefix}{self.sequence:04d}"

    def generate_share_link(self):
        """Generate and save the shareadble link to the customer."""
        self.share_link_id = uuid.uuid4()
        self.save()

    def save(self, *args, **kwargs):

        # Recalculate totals from active items only (soft-deleted items are excluded).
        if self.pk:
            active_items = self.items.filter(is_active=True)
            self.total_amount = sum(
                (item.total_amount or Decimal("0") for item in active_items),
                Decimal("0"),
            )
            self.vat_rate_amount = (
                self.total_amount * Decimal(self.vat_rate) / Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            self.total_amount_final = self.total_amount + self.vat_rate_amount

        if self.number:
            return super().save(*args, **kwargs)

        # Two invoices created at the same moment can race for the same
        # number; the unique constraint catches it and we take the next one.
        attempts = 5
        for attempt in range(attempts):
            self._assign_number()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                if attempt == attempts - 1:
                    raise


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        related_name="items",
        on_delete=models.CASCADE,
        null=True,
    )
    description = models.CharField(
        max_length=512,
        null=True,
    )
    title = models.CharField(
        max_length=255,
        null=True,
    )
    amount = models.DecimalField(
        max_digits=19,
        decimal_places=2,
    )
    quantity = models.PositiveIntegerField(
        default=1,
    )
    total_amount = models.DecimalField(
        max_digits=19,
        decimal_places=2,
        null=True,
    )
    is_active = models.BooleanField(
        default=True,
        null=True,
    )

    def __str__(self):
        return f"{self.description} (x{self.quantity}) - ${self.amount}"

    def save(self, *args, **kwargs):
        """Update the total price."""
        self.total_amount = self.quantity * self.amount
        return super().save(*args, **kwargs)


class BusinessProfile(models.Model):
    """Sender details printed on a user's invoices (one per user)."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="business_profile",
    )
    business_name = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    tax_id = models.CharField(max_length=64, blank=True, verbose_name="VAT / tax ID")
    payment_instructions = models.TextField(
        blank=True,
        help_text="Shown below the totals, e.g. bank details.",
    )
    footer_note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.business_name or f"Business profile of {self.user}"

    @classmethod
    def for_user(cls, user):
        """Return the user's profile, creating an empty one if needed."""
        profile, _ = cls.objects.get_or_create(user=user)
        return profile

    @classmethod
    def for_user_readonly(cls, user):
        """Return the user's saved profile, or an unsaved empty one.

        For read-only paths (e.g. rendering a PDF from a public share link)
        where creating a database row as a side effect is undesirable.
        """
        try:
            return cls.objects.get(user=user)
        except cls.DoesNotExist:
            return cls(user=user)
