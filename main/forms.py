from django import forms
from .models import Invoice, InvoiceItem

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['client', 'due_date', 'status']  # Include fields you want to allow users to edit

class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['description', 'amount', 'quantity']

class InvoiceItemFormSet(forms.BaseFormSet):
    def clean(self):
        super().clean()
        if not self.forms:
            raise forms.ValidationError("At least one item is required.")