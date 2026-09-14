from django.contrib import admin
from .models import (
    Supplier, PurchaseRequest, PurchaseRequestLine, PurchaseQuotation,
    PurchaseQuotationLine, PurchaseOrder, PurchaseOrderLine, GoodsReceipt,
    GoodsReceiptLine, APInvoice, APInvoiceLine, APCreditMemo, APCreditMemoLine,
    OutgoingPayment,
)


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("supplier_code", "name", "phone", "email", "is_active")
    search_fields = ("supplier_code", "name", "phone", "email")


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ("request_number", "requested_by_name", "department", "request_date", "status")
    list_filter = ("status",)


@admin.register(PurchaseQuotation)
class PurchaseQuotationAdmin(admin.ModelAdmin):
    list_display = ("quotation_number", "supplier", "quotation_date", "status")
    list_filter = ("status",)


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "supplier", "order_date", "status")
    list_filter = ("status",)


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "supplier", "receipt_date", "status")
    list_filter = ("status",)


@admin.register(APInvoice)
class APInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "supplier", "invoice_date", "status")
    list_filter = ("status",)


@admin.register(APCreditMemo)
class APCreditMemoAdmin(admin.ModelAdmin):
    list_display = ("credit_memo_number", "supplier", "credit_date", "status")
    list_filter = ("status",)


@admin.register(OutgoingPayment)
class OutgoingPaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_number", "supplier", "payment_date", "amount", "status")
    list_filter = ("status",)


admin.site.register(PurchaseRequestLine)
admin.site.register(PurchaseQuotationLine)
admin.site.register(PurchaseOrderLine)
admin.site.register(GoodsReceiptLine)
admin.site.register(APInvoiceLine)
admin.site.register(APCreditMemoLine)