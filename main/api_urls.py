from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .api_views import (
    ClientViewSet, InvoiceViewSet, InvoiceItemViewSet,
    PublicInvoiceView, PublicInvoicePdfView
)

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'invoice-items', InvoiceItemViewSet, basename='invoiceitem')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', obtain_auth_token, name='api_token_auth'),
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),
    # Public, unauthenticated share-link endpoints
    path('public/invoices/<uuid:share_link_id>/', PublicInvoiceView.as_view(), name='public_invoice'),
    path('public/invoices/<uuid:share_link_id>/pdf/', PublicInvoicePdfView.as_view(), name='public_invoice_pdf'),
]
