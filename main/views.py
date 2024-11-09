from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView , TemplateView
from django.forms import modelformset_factory
from django.shortcuts import render
from .models import Invoice, InvoiceItem
from .forms import InvoiceForm, InvoiceItemForm, InvoiceItemFormSet

class HomeView(TemplateView):
    template_name ="main/pages/index.html"

def get_in(request):
    return render(request,"main/pages/invoice_form.html")

class InvoiceCreateView(CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'main/pages/invoice_form.html'
    success_url = reverse_lazy('invoice-list')  # Redirect after successful creation

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = InvoiceItemFormSet(self.request.POST)
        else:
            context['formset'] = InvoiceItemFormSet(queryset=InvoiceItem.objects.none())
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            invoice = form.save(commit=False)
            invoice.user = self.request.user  # Set the user from the request
            invoice.save()
            items = formset.save(commit=False)
            for item in items:
                item.invoice = invoice
                item.save()
            return super().form_valid(form)
        else:
            return self.form_invalid(form)

class InvoiceListView(ListView):
    model = Invoice
    template_name = 'main/pages/invoice_list.html'
    context_object_name = 'invoices'
    
    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user)  # Filter by logged-in user