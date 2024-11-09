from django.urls import path
from .views import InvoiceCreateView, InvoiceListView , HomeView , get_in

urlpatterns = [
    path('',HomeView.as_view() , name="home"),
   # path('invoices/new/', InvoiceCreateView.as_view(), name='invoice-create'),
    path('invoices/new/', get_in, name='invoice-create'),
    path('invoices/', InvoiceListView.as_view(), name='invoice-list'),
]