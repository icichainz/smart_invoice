from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from .models import Client, Invoice, InvoiceItem
from .pdf import build_invoice_pdf
from .serializers import (
    ClientSerializer, InvoiceSerializer, InvoiceCreateSerializer,
    InvoiceItemSerializer, InvoiceItemCreateSerializer,
    PublicInvoiceSerializer
)


def invoice_pdf_response(invoice):
    """Wrap a rendered invoice PDF in a downloadable HTTP response."""
    response = HttpResponse(build_invoice_pdf(invoice), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.id}.pdf"'
    return response


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'email']
    ordering_fields = ['name']
    ordering = ['name']

    def get_queryset(self):
        # Users can only see their own clients
        return Client.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class InvoiceViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'save_as_draft', 'is_closed', 'sent']
    search_fields = ['client__name', 'client__email']
    ordering_fields = ['created_at', 'due_date', 'total_amount_final']
    ordering = ['-created_at']

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return InvoiceCreateSerializer
        return InvoiceSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def save_as_draft(self, request, pk=None):
        """Save invoice as draft"""
        invoice = self.get_object()
        invoice.save_as_draft = True
        invoice.is_closed = False
        invoice.save()
        
        serializer = self.get_serializer(invoice)
        return Response({
            'status': 'success',
            'message': 'Invoice saved as draft',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        """Finalize invoice (save and close)"""
        invoice = self.get_object()
        invoice.save_as_draft = False
        invoice.is_closed = True
        invoice.save()
        
        serializer = self.get_serializer(invoice)
        return Response({
            'status': 'success',
            'message': 'Invoice finalized successfully',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def copy(self, request, pk=None):
        """Create a copy of an existing invoice"""
        original_invoice = self.get_object()
        
        # Create new invoice copy
        new_invoice = Invoice.objects.create(
            client=original_invoice.client,
            user=request.user,
            vat_rate=original_invoice.vat_rate,
            save_as_draft=True
        )
        
        # Copy all active items
        for item in original_invoice.items.filter(is_active=True):
            InvoiceItem.objects.create(
                invoice=new_invoice,
                title=item.title,
                description=item.description,
                amount=item.amount,
                quantity=item.quantity
            )
        
        new_invoice.save()  # Trigger total calculation
        
        serializer = self.get_serializer(new_invoice)
        return Response({
            'status': 'success',
            'message': 'Invoice copied successfully',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def generate_share_link(self, request, pk=None):
        """Generate shareable link for invoice"""
        invoice = self.get_object()
        invoice.generate_share_link()
        
        serializer = self.get_serializer(invoice)
        return Response({
            'status': 'success',
            'message': 'Share link generated',
            'data': serializer.data
        })

    @action(detail=True, methods=['post'])
    def revoke_share_link(self, request, pk=None):
        """Revoke the shareable link for invoice"""
        invoice = self.get_object()
        invoice.share_link_id = None
        invoice.save()
        
        serializer = self.get_serializer(invoice)
        return Response({
            'status': 'success',
            'message': 'Share link revoked',
            'data': serializer.data
        })

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """Download invoice as PDF"""
        invoice = self.get_object()
        return invoice_pdf_response(invoice)


class InvoiceItemViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['invoice', 'is_active']
    ordering_fields = ['id', 'title', 'amount']
    ordering = ['id']

    def get_queryset(self):
        return InvoiceItem.objects.filter(invoice__user=self.request.user)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return InvoiceItemCreateSerializer
        return InvoiceItemSerializer

    def destroy(self, request, *args, **kwargs):
        """Soft delete - mark as inactive instead of actual deletion"""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        
        # Trigger invoice total recalculation
        if instance.invoice:
            instance.invoice.save()
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted item"""
        item = self.get_object()
        item.is_active = True
        item.save()
        
        # Trigger invoice total recalculation
        if item.invoice:
            item.invoice.save()
        
        serializer = self.get_serializer(item)
        return Response({
            'status': 'success',
            'message': 'Item restored successfully',
            'data': serializer.data
        })


def get_shared_invoice_or_404(share_link_id):
    """Look up a non-draft invoice by its public share link id."""
    return get_object_or_404(
        Invoice.objects.select_related('client'),
        share_link_id=share_link_id,
        save_as_draft=False,
    )


class PublicInvoiceView(APIView):
    """Read-only, unauthenticated view of an invoice via its share link."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, share_link_id):
        invoice = get_shared_invoice_or_404(share_link_id)
        serializer = PublicInvoiceSerializer(invoice)
        return Response(serializer.data)


class PublicInvoicePdfView(APIView):
    """Unauthenticated PDF download of an invoice via its share link."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, share_link_id):
        invoice = get_shared_invoice_or_404(share_link_id)
        return invoice_pdf_response(invoice)
