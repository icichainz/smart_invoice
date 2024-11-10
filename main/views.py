from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView , TemplateView
from django.forms import modelformset_factory
from django.shortcuts import render
from django.http import JsonResponse
from .models import Invoice, InvoiceItem , Client, InvoiceSeed
from .forms import InvoiceForm, InvoiceItemForm, InvoiceItemFormSet

class HomeView(TemplateView):
    template_name ="main/pages/index.html"


def pool_total_amount_value(request,seed_id):
    pass

def  add_invoice_item(request):
    if request.method == "POST":
        invoice_item_form = InvoiceItemForm(request.POST)
        if invoice_item_form.is_valid():
            new_item = invoice_item_form.save(commit=True)
            f_obj = InvoiceItem.objects.filter(invoice_seed=new_item.invoice_seed)
            total_amount = sum(for amount in f_obj.amount)
        



            return JsonResponse(data=[])
def edit_invoice_item(request):
    pass 

def remove_invoice_item(request):
    pass 

def update_client_info(request):
    if request.method == "POST":
        client_id = request.POST.get('client_id')
        field_name = request.POST.get('client_field_name')
        field_value = request.POST.get('client_field_value')
        client = Client.objects.filter(id=client_id)
    pass 




def create_invoice(request):
    inv_seed = InvoiceSeed(
        user = request.user
    )

    return render(
        request=request,
        template_name="main/pages/invoice_form.html",
        context = {
            'invoice_seed': inv_seed ,
        }
    )

#todo: add filters.
class InvoiceListView(ListView):
    model = Invoice
    template_name = 'main/pages/invoice_list.html'
    context_object_name = 'invoices'
    
    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user)  # Filter by logged-in user