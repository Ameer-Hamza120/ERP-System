from django.contrib import admin
from .models import (
    Customer, SalesQuotation, SalesQuotationLine, SalesOrder, SalesOrderLine,
    Delivery, DeliveryLine, ReturnRequest, ReturnRequestLine, SalesReturn,
    SalesReturnLine, ARInvoice, ARInvoiceLine, ARCreditMemo, ARCreditMemoLine,
    IncomingPayment,
)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("customer_code", "name", "phone", "email", "is_active")
    search_fields = ("customer_code", "name", "phone", "email")


@admin.register(SalesQuotation)
class SalesQuotationAdmin(admin.ModelAdmin):
    list_display = ("quotation_number", "customer", "quotation_date", "status")
    list_filter = ("status",)


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "customer", "order_date", "status")
    list_filter = ("status",)


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("delivery_number", "customer", "delivery_date", "status")
    list_filter = ("status",)


@admin.register(SalesReturn)
class SalesReturnAdmin(admin.ModelAdmin):
    list_display = ("return_number", "customer", "return_date", "status")
    list_filter = ("status",)


@admin.register(ARInvoice)
class ARInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "customer", "invoice_date", "status")
    list_filter = ("status",)


@admin.register(ARCreditMemo)
class ARCreditMemoAdmin(admin.ModelAdmin):
    list_display = ("credit_memo_number", "customer", "credit_date", "status")
    list_filter = ("status",)


@admin.register(IncomingPayment)
class IncomingPaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_number", "customer", "payment_date", "amount", "status")
    list_filter = ("status",)


admin.site.register(SalesQuotationLine)
admin.site.register(SalesOrderLine)
admin.site.register(DeliveryLine)
admin.site.register(ReturnRequest)
admin.site.register(ReturnRequestLine)
admin.site.register(SalesReturnLine)
admin.site.register(ARInvoiceLine)
admin.site.register(ARCreditMemoLine)