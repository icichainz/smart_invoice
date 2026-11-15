from django.contrib import admin
from .models import BusinessProfile, Client, Invoice, InvoiceItem

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1  # Number of empty forms to display

class InvoiceAdmin(admin.ModelAdmin):
    inlines = [InvoiceItemInline]
    list_display = ("number", "client", "user", "status", "total_amount_final", "created_at")
    list_filter = ("status", "user")
    search_fields = ("number", "client__name")
    readonly_fields = ("number",)

class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "user")
    list_filter = ("user",)
    search_fields = ("name", "email")

admin.site.register(Client, ClientAdmin)
admin.site.register(Invoice, InvoiceAdmin)


class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "business_name", "email", "phone")
    search_fields = ("business_name", "email", "user__username")


admin.site.register(BusinessProfile, BusinessProfileAdmin)
