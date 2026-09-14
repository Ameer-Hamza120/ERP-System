from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from inventory.models import Item, Warehouse


from accounts.models import get_next_document_number as _next_number


class BaseDocument(models.Model):
    """Common fields shared by every sales document header."""

    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseLine(models.Model):
    """Common line-item fields shared by every sales document."""

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


class Customer(models.Model):
    customer_code = models.CharField(max_length=50, unique=True, blank=True)
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
        if not self.customer_code:
            from accounts.models import DocumentSequence

            seq, _ = DocumentSequence.objects.get_or_create(
                document_type="CUST",
                defaults={
                    "prefix": "CUS",
                    "include_year": False,
                    "next_number": Customer.objects.count() + 1,
                },
            )
            self.customer_code = DocumentSequence.get_next("CUST")
        super().save(*args, **kwargs)

    @property
    def receivable(self):
        """Total amount the customer owes the company (A/R balance)."""
        from django.db.models import Sum

        invoice_total = sum(
            inv.total for inv in self.arinvoices.exclude(status="Cancelled")
        )
        paid = self.incoming_payments.filter(status="Completed").aggregate(
            total=Sum("amount")
        )["total"] or 0
        credit = sum(
            cm.total for cm in self.arcreditmemos.exclude(status="Cancelled")
        )
        return self.opening_balance + invoice_total - paid - credit


class SalesQuotation(BaseDocument):
    """A. Sales Quotation - price offer given to a customer."""

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Open", "Open"),
        ("Accepted", "Accepted"),
        ("Expired", "Expired"),
        ("Cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Draft")
    quotation_number = models.CharField(max_length=30, unique=True, blank=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="sales_quotations"
    )
    quotation_date = models.DateField(default=timezone.now)
    valid_until = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.quotation_number or "Quotation"

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), 0)

    def save(self, *args, **kwargs):
        if not self.quotation_number:
            self.quotation_number = _next_number("SQ", "SQ")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class SalesQuotationLine(BaseLine):
    quotation = models.ForeignKey(
        SalesQuotation, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.quantity} x {self.item.name}"


class SalesOrder(BaseDocument):
    """B. Sales Order - customer confirms they want to buy."""

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Open", "Open"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Draft")
    order_number = models.CharField(max_length=30, unique=True, blank=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="sales_orders"
    )
    quotation = models.ForeignKey(
        SalesQuotation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True, blank=True
    )
    order_date = models.DateField(default=timezone.now)
    required_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.order_number or "Order"

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), 0)

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = _next_number("SO", "SO")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class SalesOrderLine(BaseLine):
    order = models.ForeignKey(
        SalesOrder, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.quantity} x {self.item.name}"


class Delivery(BaseDocument):
    """C. Delivery - goods sent to the customer (stock decreases)."""

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Posted", "Posted"),
        ("Cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Draft")
    delivery_number = models.CharField(max_length=30, unique=True, blank=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="deliveries"
    )
    order = models.ForeignKey(
        SalesOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries"
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    delivery_date = models.DateField(default=timezone.now)

    def __str__(self):
        return self.delivery_number or "Delivery"

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), 0)

    def save(self, *args, **kwargs):
        if not self.delivery_number:
            self.delivery_number = _next_number("DLV", "DLV")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class DeliveryLine(BaseLine):
    delivery = models.ForeignKey(
        Delivery, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.quantity} x {self.item.name}"


class ReturnRequest(BaseDocument):
    """D. Return Request - track a customer's request to return goods."""

    STATUS_CHOICES = [
        ("Open", "Open"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
        ("Cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Open")
    request_number = models.CharField(max_length=30, unique=True, blank=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="return_requests"
    )
    order = models.ForeignKey(
        SalesOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name="return_requests"
    )
    request_date = models.DateField(default=timezone.now)
    reason = models.TextField(blank=True)

    def __str__(self):
        return self.request_number or "Return Request"

    def save(self, *args, **kwargs):
        if not self.request_number:
            self.request_number = _next_number("RR", "RR")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class ReturnRequestLine(BaseLine):
    return_request = models.ForeignKey(
        ReturnRequest, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    reason = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.quantity} x {self.item.name}"


class SalesReturn(BaseDocument):
    """E. Return - goods actually come back to the company (stock increases)."""

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Posted", "Posted"),
        ("Cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Draft")
    return_number = models.CharField(max_length=30, unique=True, blank=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="sales_returns"
    )
    request = models.ForeignKey(
        ReturnRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="returns"
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    return_date = models.DateField(default=timezone.now)

    def __str__(self):
        return self.return_number or "Return"

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), 0)

    def save(self, *args, **kwargs):
        if not self.return_number:
            self.return_number = _next_number("RTN", "RTN")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class SalesReturnLine(BaseLine):
    return_doc = models.ForeignKey(
        SalesReturn, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    reason = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.quantity} x {self.item.name}"


class ARInvoice(BaseDocument):
    """F. A/R Invoice - money the customer owes us."""

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Open", "Open"),
        ("Partial", "Partially Paid"),
        ("Paid", "Paid"),
        ("Cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Draft")
    invoice_number = models.CharField(max_length=30, unique=True, blank=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="arinvoices"
    )
    order = models.ForeignKey(
        SalesOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name="arinvoices"
    )
    delivery = models.ForeignKey(
        Delivery, on_delete=models.SET_NULL, null=True, blank=True, related_name="arinvoices"
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
            self.invoice_number = _next_number("INV", "INV")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class ARInvoiceLine(BaseLine):
    invoice = models.ForeignKey(
        ARInvoice, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.quantity} x {self.item.name}"


class ARCreditMemo(BaseDocument):
    """G. A/R Credit Memo - reduce the customer's receivable."""

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Open", "Open"),
        ("Applied", "Applied"),
        ("Cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Draft")
    credit_memo_number = models.CharField(max_length=30, unique=True, blank=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="arcreditmemos"
    )
    return_doc = models.ForeignKey(
        SalesReturn, on_delete=models.SET_NULL, null=True, blank=True, related_name="credit_memos"
    )
    credit_date = models.DateField(default=timezone.now)

    def __str__(self):
        return self.credit_memo_number or "Credit Memo"

    @property
    def total(self):
        return sum((line.line_total for line in self.lines.all()), 0)

    def save(self, *args, **kwargs):
        if not self.credit_memo_number:
            self.credit_memo_number = _next_number("CRM", "CRM")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]


class ARCreditMemoLine(BaseLine):
    credit_memo = models.ForeignKey(
        ARCreditMemo, on_delete=models.CASCADE, related_name="lines"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.quantity} x {self.item.name}"


class IncomingPayment(BaseDocument):
    """H. Incoming Payment - customer pays the company."""

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
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="incoming_payments"
    )
    invoice = models.ForeignKey(
        ARInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )
    payment_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default="Cash")
    reference = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.payment_number or "Payment"

    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = _next_number("IP", "IP")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        if self.amount <= 0:
            raise ValidationError("Payment amount must be greater than 0.")
