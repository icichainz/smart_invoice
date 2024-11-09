from django.contrib import admin
from .models import Client, Invoice, InvoiceItem

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1  # Number of empty forms to display

class InvoiceAdmin(admin.ModelAdmin):
    inlines = [InvoiceItemInline]

admin.site.register(Client)
admin.site.register(Invoice, InvoiceAdmin)