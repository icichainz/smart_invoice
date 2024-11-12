from django import forms
from django.forms import inlineformset_factory
from .models import Invoice, InvoiceItem


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            "client",
            "due_date",
            "status",
        ]  # Include fields you want to allow users to edit


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = [
            "invoice",
            "description",
            "amount",
            "quantity",
            "title",
        ]
