from django.urls import path
from .views import (
    create_invoice,
    InvoiceListView,
    HomeView,
    add_invoice_item,
    update_invoice_item,
    delete_invoice_item,
    get_add_invoice_item_form,
    get_edit_item_form,
)

urlpatterns = [
    path(
        "",
        HomeView.as_view(),
        name="home",
    ),
    # path('invoices/new/', InvoiceCreateView.as_view(), name='invoice-create'),
    path(
        "invoices/new/",
        create_invoice,
        name="invoice-create",
    ),
    path(
        "invoices/",
        InvoiceListView.as_view(),
        name="invoice-list",
    ),
    path(
        "items/new/",
        add_invoice_item,
        name="add_invoice_item",
    ),
    path(
        "items/<int:item_id>/edit/",
        update_invoice_item,
        name="edit_invoice_item",
    ),
    path(
        "items/<int:id>/remove/",
        delete_invoice_item,
        name="delete_invoice_item",
    ),
    path(
        "get-item-add-form/",
        get_add_invoice_item_form,
        name="get_item_add_form",
    ),
    path(
        "get-item-edit-form/<int:item_id>/",
        get_edit_item_form,
        name="get_item_edit",
    ),
]
