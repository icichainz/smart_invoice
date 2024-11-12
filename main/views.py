from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView
from django.forms import modelformset_factory
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse,HttpResponse
from .models import Invoice, InvoiceItem, Client
from .forms import InvoiceForm, InvoiceItemForm


class HomeView(TemplateView):
    template_name = "main/pages/index.html"


@login_required
def get_add_invoice_item_form(request):
    invoice_id = request.GET.get('invoice_id')
    return render(
        request=request,
        template_name="main/components/item_add_form.html",
        context={
            'invoice_id':invoice_id
        }
    )

@login_required
def get_edit_item_form(request,item_id):
    return render(
        request=request,
        template_name="main/components/item_edit_form.html",
        context={
            'item':InvoiceItem.objects.get(id=item_id)
        }
    )

@login_required()
def add_invoice_item(request):
    if request.method == "POST":
        invoice_item_form = InvoiceItemForm(request.POST)
        print(invoice_item_form.data)

        if invoice_item_form.is_valid():
            new_invoice_item = invoice_item_form.save()
            new_invoice_item.invoice.save()
            return render(
                request,
                "main/components/invoice_table.html",
                {"invoice": new_invoice_item.invoice},
            )
 


@login_required()
def update_invoice_item(request, item_id):
    invoice_item = get_object_or_404(InvoiceItem, id=item_id)

    if request.method == "POST":
        invoice_item_form = InvoiceItemForm(
            request.POST,
            instance=invoice_item,
        )

        if invoice_item_form.is_valid():
            updated_invoice_item = invoice_item_form.save()
            return render(
                request,
                "main/components/invoice_table.html",
                {"invoice": updated_invoice_item.invoice},
            )


@login_required()
def delete_invoice_item(request, item_id):
    invoice_item = get_object_or_404(InvoiceItem, id=item_id)

    if request.method == "POST":
        invoice_item.is_active = False
        invoice_item.save()
        return render(
            request,
            "main/components/invoice_table.html",
            {"invoice": invoice_item.invoice},
        )


def update_client_info(request):
    if request.method == "POST":
        client_id = request.POST.get("client_id")
        field_name = request.POST.get("client_field_name")
        field_value = request.POST.get("client_field_value")
        client = Client.objects.filter(id=client_id)
    pass

@login_required
def create_invoice(request):
    try:
        last_invoice = Invoice.objects.filter(is_closed=False).latest('id')
        invoice_to_use = last_invoice
    except Invoice.DoesNotExist:
        invoice_to_use = Invoice.objects.create(user=request.user)
    print(f'Invoice to use id : {invoice_to_use.id}')
    return render(
        request=request,
        template_name="main/pages/invoice_form.html",
        context={
            "invoice": invoice_to_use,
        },
    )


def save_invoice(request):
    pass


def save_as_draft(request,invoice_id,):
    pass


def create_new_from_copy(request):
    pass


# todo: add filters.
class InvoiceListView(ListView):
    model = Invoice
    template_name = "main/pages/invoice_list.html"
    context_object_name = "invoices"

    def get_queryset(self):
        return Invoice.objects.filter(
            user=self.request.user
        )  # Filter by logged-in user
