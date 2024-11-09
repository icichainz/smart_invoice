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
        ('unpaid', 'Unpaid'),
        ('paid', 'Paid'),
    )
    EMAIL_CHOICES = (
        ('sent','Sent'),
        ('not sent','Not Sent')
    )

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_draft = models.BooleanField(default=False)
    sent = models.CharField(max_length=10,choices=EMAIL_CHOICES,default="not sent")

    def __str__(self):
        return f"Invoice #{self.id} for {self.client.name} - Status: {self.status}"

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name='items', on_delete=models.CASCADE)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.description} (x{self.quantity}) - ${self.amount}"
