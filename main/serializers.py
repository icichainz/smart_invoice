from rest_framework import serializers
from django.contrib.auth.models import User
from .models import BusinessProfile, Client, Invoice, InvoiceItem


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'email', 'phone']
        read_only_fields = ['id']

    def validate_email(self, value):
        if value and not value.strip():
            raise serializers.ValidationError("Email cannot be empty.")
        return value


def validate_owned_client(serializer, value):
    """Only allow referencing clients owned by the requesting user."""
    if value is None:
        return value
    # Keep an invoice's existing client valid even if it predates ownership
    # (clients the migration could not backfill have no owner).
    instance = getattr(serializer, 'instance', None)
    if instance is not None and instance.client_id == value.pk:
        return value
    request = serializer.context.get('request')
    if request is None or value.user_id != request.user.id:
        raise serializers.ValidationError("Client not found.")
    return value


class InvoiceItemSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(max_digits=19, decimal_places=2, read_only=True)
    
    class Meta:
        model = InvoiceItem
        fields = [
            'id', 'title', 'description', 'amount', 'quantity', 
            'total_amount', 'is_active'
        ]
        read_only_fields = ['id', 'total_amount']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True)
    total_amount = serializers.DecimalField(max_digits=22, decimal_places=2, read_only=True)
    total_amount_final = serializers.DecimalField(max_digits=22, decimal_places=2, read_only=True)
    vat_rate_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'number', 'client', 'client_name', 'user', 'user_name',
            'created_at', 'due_date', 'vat_rate', 'total_amount',
            'total_amount_final', 'vat_rate_amount', 'status',
            'save_as_draft', 'is_closed', 'share_link_id', 'sent', 'sent_at', 'items'
        ]
        read_only_fields = [
            'id', 'number', 'created_at', 'total_amount', 'total_amount_final', 
            'vat_rate_amount', 'share_link_id', 'sent_at', 'user', 'client_name', 'user_name'
        ]

    def validate_client(self, value):
        return validate_owned_client(self, value)

    def validate_vat_rate(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("VAT rate must be between 0 and 100.")
        return value


class SendInvoiceEmailSerializer(serializers.Serializer):
    """Optional note included in the email sent to the client."""
    message = serializers.CharField(
        max_length=2000, allow_blank=True, default=''
    )


class InvoiceCreateSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, required=False)
    
    class Meta:
        model = Invoice
        fields = [
            'client', 'due_date', 'vat_rate', 'status',
            'save_as_draft', 'sent', 'items'
        ]

    def validate_client(self, value):
        return validate_owned_client(self, value)

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        invoice = Invoice.objects.create(**validated_data)
        
        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)
            
        invoice.save()  # Trigger total calculation
        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', [])
        
        # Update invoice fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update items if provided
        if items_data:
            # Deactivate existing items
            instance.items.update(is_active=False)
            
            # Create new items
            for item_data in items_data:
                InvoiceItem.objects.create(invoice=instance, **item_data)
        
        instance.save()  # Trigger total calculation
        return instance


class InvoiceItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ['invoice', 'title', 'description', 'amount', 'quantity']
        extra_kwargs = {'invoice': {'allow_null': False, 'required': True}}

    def validate_invoice(self, value):
        """Only allow attaching items to invoices owned by the requesting user."""
        request = self.context.get('request')
        if request is None or value.user_id != request.user.id:
            raise serializers.ValidationError("Invoice not found.")
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value

    def create(self, validated_data):
        item = super().create(validated_data)
        # Trigger invoice total recalculation
        if item.invoice:
            item.invoice.save()
        return item

    def update(self, instance, validated_data):
        previous_invoice = instance.invoice
        item = super().update(instance, validated_data)
        # Trigger invoice total recalculation
        if item.invoice:
            item.invoice.save()
        if previous_invoice and previous_invoice != item.invoice:
            previous_invoice.save()
        return item


class PublicInvoiceItemSerializer(serializers.ModelSerializer):
    total_amount = serializers.DecimalField(max_digits=19, decimal_places=2, read_only=True)

    class Meta:
        model = InvoiceItem
        fields = ['title', 'description', 'amount', 'quantity', 'total_amount']
        read_only_fields = fields


class PublicInvoiceSerializer(serializers.ModelSerializer):
    """Customer-facing invoice served via share links; omits owner and internal fields."""
    items = serializers.SerializerMethodField()
    client_name = serializers.CharField(source='client.name', read_only=True, default=None)
    client_email = serializers.EmailField(source='client.email', read_only=True, default=None)
    total_amount = serializers.DecimalField(max_digits=22, decimal_places=2, read_only=True)
    total_amount_final = serializers.DecimalField(max_digits=22, decimal_places=2, read_only=True)
    vat_rate_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'number', 'created_at', 'due_date', 'status', 'vat_rate',
            'total_amount', 'vat_rate_amount', 'total_amount_final',
            'client_name', 'client_email', 'items'
        ]
        read_only_fields = fields

    def get_items(self, obj):
        active_items = obj.items.filter(is_active=True).order_by('id')
        return PublicInvoiceItemSerializer(active_items, many=True).data


class BusinessProfileSerializer(serializers.ModelSerializer):
    """The current user's sender details, as printed on their invoices."""

    class Meta:
        model = BusinessProfile
        fields = [
            'business_name', 'address', 'email', 'phone', 'tax_id',
            'payment_instructions', 'footer_note'
        ]
