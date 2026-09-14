from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from inventory.models import Item, Warehouse


from accounts.models import get_next_document_number as _next_number


class BaseDocument(models.Model):
    """Common fields shared by every purchasing document header."""

    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseLine(models.Model):
    """Common line-item fields shared by every purchasing document."""

    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    @property
    def line_total(self):
        subtotal = self.quantity * self.unit_price
        discount = subtotal * self.discount_percent / 100
        net = subtotal - discount
        tax = net * self.tax_percent / 100
        return net + tax

    class Meta:
        abstract = True

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than 0.")
        if self.unit_price < 0:
            raise ValidationError("Unit price cannot be negative.")
        if self.discount_percent < 0 or self.discount_percent > 100:
            raise ValidationError("Discount percent must be between 0 and 100.")
        if self.tax_percent < 0:
            raise ValidationError("Tax percent cannot be negative.")


class Supplier(models.Model):
    supplier_code = models.CharField(max_length=50, unique=True, blank=True)
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    payment_terms = models.CharField(max_length=100, blank=True)
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.supplier_code:
            from accounts.models import DocumentSequence

            seq, _ = DocumentSequence.objects.get_or_create(
                document_type="SUPP",
                defaults={
                    "prefix": "SUP",
                    "include_year": False,
                    "next_number": Supplier.objects.count() + 1,
                },
            )
            self.supplier_code = DocumentSequence.get_next("SUPP")
        super().save(*args, **kwargs)

    @property
    def payable(self):
        """Total amount the company owes the supplier (A/P balance)."""
        from django.db.models import Sum

        invoice_total = sum(
            inv.total for inv in self.apinvoices.exclude(status="Cancelled")
        )
        paid = self.outgoing_payments.filter(status="Completed").aggregate(
            total=Sum("amount")
        )["total"] or 0
        credit = sum(
            cm.total for cm in self.apcreditmemos.exclude(status="Cancelled")
        )
        return self.opening_balance + invoice_total - paid - credit


class PurchaseRequest(BaseDocument):
    """A. Purchase Request - an employee/department requests something."""

    STATUS_CHOICES = [
        ("Open", "Open"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
        ("Cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Open")
    request_number = models.CharField(max_length=30, unique=True, blank=True)
    requested_by_name = models.CharField(max_length=200, blank=True)
    department = models.CharField(max_length=100, blank=True)
    request_date = models.DateField(default=timezone.now)
    required_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.request_number or "Purchase Request"

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), 0)

    def save(self, *args, **kwargs):
        if not self.request_number:
            self.request_number = _next_number("PR", "PR")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class PurchaseRequestLine(BaseLine):
    purchase_request = models.ForeignKey(
        PurchaseRequest, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    reason = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.quantity} x {self.item.name}"


class PurchaseQuotation(BaseDocument):
    """B. Purchase Quotation - supplier gives you a price."""

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Open", "Open"),
        ("Accepted", "Accepted"),
        ("Rejected", "Rejected"),
        ("Cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Draft")
    quotation_number = models.CharField(max_length=30, unique=True, blank=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="purchase_quotations"
    )
    request = models.ForeignKey(
        PurchaseRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="quotations"
    )
    quotation_date = models.DateField(default=timezone.now)
    valid_until = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.quotation_number or "Purchase Quotation"

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), 0)

    def save(self, *args, **kwargs):
        if not self.quotation_number:
            self.quotation_number = _next_number("PQ", "PQ")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class PurchaseQuotationLine(BaseLine):
    quotation = models.ForeignKey(
        PurchaseQuotation, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.quantity} x {self.item.name}"


class PurchaseOrder(BaseDocument):
    """C. Purchase Order - company officially orders from the supplier."""

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Open", "Open"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Draft")
    order_number = models.CharField(max_length=30, unique=True, blank=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="purchase_orders"
    )
    quotation = models.ForeignKey(
        PurchaseQuotation, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True, blank=True
    )
    order_date = models.DateField(default=timezone.now)
    expected_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.order_number or "Purchase Order"

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), 0)

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = _next_number("PO", "PO")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class PurchaseOrderLine(BaseLine):
    order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.quantity} x {self.item.name}"


class GoodsReceipt(BaseDocument):
    """D. Goods Receipt PO - goods arrive from supplier (stock increases)."""

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Posted", "Posted"),
        ("Cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Draft")
    receipt_number = models.CharField(max_length=30, unique=True, blank=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="goods_receipts"
    )
    order = models.ForeignKey(
        PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name="goods_receipts"
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    receipt_date = models.DateField(default=timezone.now)

    def __str__(self):
        return self.receipt_number or "Goods Receipt"

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), 0)

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = _next_number("GR", "GR")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class GoodsReceiptLine(BaseLine):
    receipt = models.ForeignKey(
        GoodsReceipt, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.quantity} x {self.item.name}"


class APInvoice(BaseDocument):
    """E. A/P Invoice - supplier sends an invoice; the company now owes them."""

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Open", "Open"),
        ("Partial", "Partially Paid"),
        ("Paid", "Paid"),
        ("Cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Draft")
    invoice_number = models.CharField(max_length=30, unique=True, blank=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="apinvoices"
    )
    order = models.ForeignKey(
        PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name="apinvoices"
    )
    goods_receipt = models.ForeignKey(
        GoodsReceipt, on_delete=models.SET_NULL, null=True, blank=True, related_name="apinvoices"
    )
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.invoice_number or "Invoice"

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), 0)

    @property
    def paid_amount(self):
        from django.db.models import Sum

        return (
            self.payments.filter(status="Completed").aggregate(total=Sum("amount"))[
                "total"
            ]
            or 0
        )

    @property
    def balance(self):
        return self.total - self.paid_amount

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = _next_number("APINV", "APINV")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class APInvoiceLine(BaseLine):
    invoice = models.ForeignKey(
        APInvoice, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.quantity} x {self.item.name}"


class APCreditMemo(BaseDocument):
    """F. A/P Credit Memo - reduce the amount payable to a supplier."""

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Open", "Open"),
        ("Applied", "Applied"),
        ("Cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Draft")
    credit_memo_number = models.CharField(max_length=30, unique=True, blank=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="apcreditmemos"
    )
    invoice = models.ForeignKey(
        APInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="credit_memos"
    )
    credit_date = models.DateField(default=timezone.now)

    def __str__(self):
        return self.credit_memo_number or "Credit Memo"

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), 0)

    def save(self, *args, **kwargs):
        if not self.credit_memo_number:
            self.credit_memo_number = _next_number("APCRM", "APCRM")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class APCreditMemoLine(BaseLine):
    credit_memo = models.ForeignKey(
        APCreditMemo, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.quantity} x {self.item.name}"


class OutgoingPayment(BaseDocument):
    """G. Outgoing Payment - company pays the supplier."""

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]
    PAYMENT_METHODS = [
        ("Cash", "Cash"),
        ("Bank Transfer", "Bank Transfer"),
        ("Cheque", "Cheque"),
        ("Card", "Card"),
        ("Other", "Other"),
    ]

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Draft")
    payment_number = models.CharField(max_length=30, unique=True, blank=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="outgoing_payments"
    )
    invoice = models.ForeignKey(
        APInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )
    payment_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="Bank Transfer")
    reference = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.payment_number or "Payment"

    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = _next_number("OP", "OP")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        if self.amount <= 0:
            raise ValidationError("Payment amount must be greater than 0.")
