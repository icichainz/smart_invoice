import uuid

from django.db import models
from django.db import models
from django.contrib.auth.models import User


class Client(models.Model):
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

    def generate_share_link(self):
        """Generate and save the shareadble link to the customer."""
        self.share_link_id = uuid.uuid4()
        self.save()

    def save(self, *args, **kwargs):

        # save  and udate
        if self.pk and self.items.exists():

            self.total_amount = sum(item.total_amount for item in self.items.all())

            if self.vat_rate:
                self.vat_rate_amount = self.total_amount * (self.vat_rate / 100)
                self.total_amount_final = self.total_amount + self.vat_rate_amount

            else:
                self.total_amount_final = self.total_amount

        return super().save(*args, **kwargs)


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
