from django.contrib import admin
from .models import Client, Invoice, InvoiceItem

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1  # Number of empty forms to display

class InvoiceAdmin(admin.ModelAdmin):
    inlines = [InvoiceItemInline]

class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "user")
    list_filter = ("user",)
    search_fields = ("name", "email")

admin.site.register(Client, ClientAdmin)
admin.site.register(Invoice, InvoiceAdmin)