from django import forms
from django.forms import inlineformset_factory

from inventory.models import Item, Warehouse

from .models import (
    ARCreditMemo,
    ARCreditMemoLine,
    ARInvoice,
    ARInvoiceLine,
    Customer,
    Delivery,
    DeliveryLine,
    IncomingPayment,
    ReturnRequest,
    ReturnRequestLine,
    SalesOrder,
    SalesOrderLine,
    SalesQuotation,
    SalesQuotationLine,
    SalesReturn,
    SalesReturnLine,
)


class CustomerForm(forms.ModelForm):
    customer_code = forms.CharField(
        required=False,
        label="Customer Code",
        help_text="Leave blank to auto-generate.",
    )

    class Meta:
        model = Customer
        fields = [
            "customer_code",
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


class _LineForm(forms.ModelForm):
    def clean(self):
        cleaned = super().clean()
        item = cleaned.get("item")
        quantity = cleaned.get("quantity") or 0
        if item and quantity:
            available = item.current_stock
            if quantity > available:
                raise forms.ValidationError(
                    f"Only {available} units of {item.name} available in stock."
                )
        return cleaned


class SalesQuotationForm(forms.ModelForm):
    class Meta:
        model = SalesQuotation
        fields = ["customer", "quotation_date", "valid_until", "remarks"]
        widgets = {
            "quotation_date": forms.DateInput(attrs={"type": "date"}),
            "valid_until": forms.DateInput(attrs={"type": "date"}),
        }


SalesQuotationLineFormSet = inlineformset_factory(
    SalesQuotation,
    SalesQuotationLine,
    fields=["item", "quantity", "unit_price", "discount_percent", "tax_percent"],
    extra=3,
    can_delete=True,
)


class SalesOrderForm(forms.ModelForm):
    class Meta:
        model = SalesOrder
        fields = ["customer", "quotation", "warehouse", "order_date", "required_date", "remarks"]
        widgets = {
            "order_date": forms.DateInput(attrs={"type": "date"}),
            "required_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["quotation"].queryset = SalesQuotation.objects.exclude(
            status="Cancelled"
        )


SalesOrderLineFormSet = inlineformset_factory(
    SalesOrder,
    SalesOrderLine,
    fields=["item", "quantity", "unit_price", "discount_percent", "tax_percent"],
    extra=3,
    can_delete=True,
)


class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ["customer", "order", "warehouse", "delivery_date", "remarks"]
        widgets = {
            "delivery_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["order"].queryset = SalesOrder.objects.exclude(status="Cancelled")


DeliveryLineFormSet = inlineformset_factory(
    Delivery,
    DeliveryLine,
    fields=["item", "quantity", "unit_price", "discount_percent", "tax_percent"],
    extra=3,
    can_delete=True,
    form=_LineForm,
)


class ReturnRequestForm(forms.ModelForm):
    class Meta:
        model = ReturnRequest
        fields = ["customer", "order", "request_date", "reason"]
        widgets = {
            "request_date": forms.DateInput(attrs={"type": "date"}),
        }


ReturnRequestLineFormSet = inlineformset_factory(
    ReturnRequest,
    ReturnRequestLine,
    fields=["item", "quantity", "unit_price", "discount_percent", "tax_percent", "reason"],
    extra=3,
    can_delete=True,
)


class SalesReturnForm(forms.ModelForm):
    class Meta:
        model = SalesReturn
        fields = ["customer", "request", "warehouse", "return_date", "remarks"]
        widgets = {
            "return_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["request"].queryset = ReturnRequest.objects.filter(
            status="Approved"
        )


SalesReturnLineFormSet = inlineformset_factory(
    SalesReturn,
    SalesReturnLine,
    fields=["item", "quantity", "unit_price", "discount_percent", "tax_percent", "reason"],
    extra=3,
    can_delete=True,
)


class ARInvoiceForm(forms.ModelForm):
    class Meta:
        model = ARInvoice
        fields = ["customer", "order", "delivery", "invoice_date", "due_date", "remarks"]
        widgets = {
            "invoice_date": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["order"].queryset = SalesOrder.objects.exclude(status="Cancelled")
        self.fields["delivery"].queryset = Delivery.objects.exclude(status="Cancelled")


ARInvoiceLineFormSet = inlineformset_factory(
    ARInvoice,
    ARInvoiceLine,
    fields=["item", "quantity", "unit_price", "discount_percent", "tax_percent"],
    extra=3,
    can_delete=True,
)


class ARCreditMemoForm(forms.ModelForm):
    class Meta:
        model = ARCreditMemo
        fields = ["customer", "return_doc", "credit_date", "remarks"]
        widgets = {
            "credit_date": forms.DateInput(attrs={"type": "date"}),
        }


ARCreditMemoLineFormSet = inlineformset_factory(
    ARCreditMemo,
    ARCreditMemoLine,
    fields=["item", "quantity", "unit_price", "discount_percent", "tax_percent"],
    extra=3,
    can_delete=True,
)


class IncomingPaymentForm(forms.ModelForm):
    class Meta:
        model = IncomingPayment
        fields = ["customer", "invoice", "payment_date", "amount", "payment_method", "reference"]
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["invoice"].queryset = ARInvoice.objects.exclude(
            status__in=["Cancelled", "Paid"]
        )
