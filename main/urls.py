from django.urls import path
from .views import create_invoice, InvoiceListView , HomeView 

urlpatterns = [
    path('',HomeView.as_view() , name="home"),
   # path('invoices/new/', InvoiceCreateView.as_view(), name='invoice-create'),
    path('invoices/new/',create_invoice , name='invoice-create'),
    path('invoices/', InvoiceListView.as_view(), name='invoice-list'),
]