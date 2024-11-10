from django import forms
from django.forms import inlineformset_factory
from .models import Invoice, InvoiceItem

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['client', 'due_date', 'status']  # Include fields you want to allow users to edit

class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['description', 'amount', 'quantity']

InvoiceItemFormSet = inlineformset_factory(
parent_model=Invoice,
model=InvoiceItem,
form=InvoiceItemForm,
extra=2,
min_num=1,
validate_min= True ,
can_delete= True ,
)