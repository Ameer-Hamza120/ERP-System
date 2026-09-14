from django import forms
from django.forms import inlineformset_factory

from inventory.models import Item, Warehouse

from .models import (
    APCreditMemo,
    APCreditMemoLine,
    APInvoice,
    APInvoiceLine,
    GoodsReceipt,
    GoodsReceiptLine,
    OutgoingPayment,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseQuotation,
    PurchaseQuotationLine,
    PurchaseRequest,
    PurchaseRequestLine,
    Supplier,
)


class SupplierForm(forms.ModelForm):
    supplier_code = forms.CharField(
        required=False,
        label="Supplier Code",
        help_text="Leave blank to auto-generate.",
    )

    class Meta:
        model = Supplier
        fields = [
            "supplier_code",
            "name",
            "contact_person",
            "phone",
            "email",
            "address",
            "city",
            "country",
            "tax_id",
            "payment_terms",
            "opening_balance",
            "is_active",
        ]


class PurchaseRequestForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequest
        fields = ["requested_by_name", "department", "request_date", "required_date", "remarks"]
        widgets = {
            "request_date": forms.DateInput(attrs={"type": "date"}),
            "required_date": forms.DateInput(attrs={"type": "date"}),
        }


PurchaseRequestLineFormSet = inlineformset_factory(
    PurchaseRequest,
    PurchaseRequestLine,
    fields=["item", "quantity", "unit_price", "discount_percent", "tax_percent", "reason"],
    extra=3,
    can_delete=True,
)


class PurchaseQuotationForm(forms.ModelForm):
    class Meta:
        model = PurchaseQuotation
        fields = ["supplier", "request", "quotation_date", "valid_until", "remarks"]
        widgets = {
            "quotation_date": forms.DateInput(attrs={"type": "date"}),
            "valid_until": forms.DateInput(attrs={"type": "date"}),
        }


PurchaseQuotationLineFormSet = inlineformset_factory(
    PurchaseQuotation,
    PurchaseQuotationLine,
    fields=["item", "quantity", "unit_price", "discount_percent", "tax_percent"],
    extra=3,
    can_delete=True,
)


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ["supplier", "quotation", "warehouse", "order_date", "expected_date", "remarks"]
        widgets = {
            "order_date": forms.DateInput(attrs={"type": "date"}),
            "expected_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["quotation"].queryset = PurchaseQuotation.objects.exclude(
            status__in=["Rejected", "Cancelled"]
        )


PurchaseOrderLineFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderLine,
    fields=["item", "quantity", "unit_price", "discount_percent", "tax_percent"],
    extra=3,
    can_delete=True,
)


class GoodsReceiptForm(forms.ModelForm):
    class Meta:
        model = GoodsReceipt
        fields = ["supplier", "order", "warehouse", "receipt_date", "remarks"]
        widgets = {
            "receipt_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["order"].queryset = PurchaseOrder.objects.exclude(
            status__in=["Completed", "Cancelled"]
        )


GoodsReceiptLineFormSet = inlineformset_factory(
    GoodsReceipt,
    GoodsReceiptLine,
    fields=["item", "quantity", "unit_price", "discount_percent", "tax_percent"],
    extra=3,
    can_delete=True,
)


class APInvoiceForm(forms.ModelForm):
    class Meta:
        model = APInvoice
        fields = ["supplier", "order", "goods_receipt", "invoice_date", "due_date", "remarks"]
        widgets = {
            "invoice_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["order"].queryset = PurchaseOrder.objects.exclude(
            status__in=["Completed", "Cancelled"]
        )
        self.fields["goods_receipt"].queryset = GoodsReceipt.objects.exclude(
            status="Cancelled"
        )


APInvoiceLineFormSet = inlineformset_factory(
    APInvoice,
    APInvoiceLine,
    fields=["item", "quantity", "unit_price", "discount_percent", "tax_percent"],
    extra=3,
    can_delete=True,
)


class APCreditMemoForm(forms.ModelForm):
    class Meta:
        model = APCreditMemo
        fields = ["supplier", "invoice", "credit_date", "remarks"]
        widgets = {
            "credit_date": forms.DateInput(attrs={"type": "date"}),
        }


APCreditMemoLineFormSet = inlineformset_factory(
    APCreditMemo,
    APCreditMemoLine,
    fields=["item", "quantity", "unit_price", "discount_percent", "tax_percent"],
    extra=3,
    can_delete=True,
)


class OutgoingPaymentForm(forms.ModelForm):
    class Meta:
        model = OutgoingPayment
        fields = ["supplier", "invoice", "payment_date", "amount", "payment_method", "reference"]
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["invoice"].queryset = APInvoice.objects.exclude(
            status__in=["Cancelled", "Paid"]
        )