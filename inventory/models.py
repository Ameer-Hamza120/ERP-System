from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class ItemGroup(models.Model):
    """
    Category or group for items.
    Example: Electronics, Furniture, Stationery.
    """

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Item(models.Model):
    """
    Item master record.
    """

    item_code = models.CharField(max_length=50, unique=True, blank=True)
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=50, blank=True)
    barcode = models.CharField(max_length=100, blank=True)
    group = models.ForeignKey(
        ItemGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name="items"
    )
    description = models.TextField(blank=True)
    unit_of_measure = models.CharField(max_length=20, default="Piece")
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True)
    minimum_stock_level = models.PositiveIntegerField(default=0)
    maximum_stock_level = models.PositiveIntegerField(blank=True, null=True)
    reorder_level = models.PositiveIntegerField(blank=True, null=True)
    image = models.ImageField(upload_to="item_images/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["item_code"]

    def __str__(self):
        return f"{self.item_code} - {self.name}"

    @property
    def current_stock(self):
        """
        Returns the total stock quantity across all warehouses.
        """
        total = self.stock_records.aggregate(total=Sum("quantity"))["total"]
        return total or 0

    def clean(self):
        if self.purchase_price < 0:
            raise ValidationError("Purchase price cannot be negative.")
        if self.selling_price < 0:
            raise ValidationError("Selling price cannot be negative.")
        if self.tax_percent < 0:
            raise ValidationError("Tax percent cannot be negative.")
        if self.minimum_stock_level < 0:
            raise ValidationError("Minimum stock level cannot be negative.")
        if self.maximum_stock_level is not None and self.maximum_stock_level < 0:
            raise ValidationError("Maximum stock level cannot be negative.")
        if self.reorder_level is not None and self.reorder_level < 0:
            raise ValidationError("Reorder level cannot be negative.")
        if (
            self.maximum_stock_level is not None
            and self.minimum_stock_level
            and self.maximum_stock_level < self.minimum_stock_level
        ):
            raise ValidationError(
                "Maximum stock level cannot be less than minimum stock level."
            )

    def save(self, *args, **kwargs):
        if not self.item_code:
            from accounts.models import DocumentSequence

            seq, _ = DocumentSequence.objects.get_or_create(
                document_type="ITEM",
                defaults={
                    "prefix": "ITM",
                    "include_year": False,
                    "next_number": Item.objects.count() + 1,
                },
            )
            self.item_code = DocumentSequence.get_next("ITEM")
        super().save(*args, **kwargs)


class Warehouse(models.Model):
    """
    A physical or logical warehouse location.
    """

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    manager = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_warehouses"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Stock(models.Model):
    """
    Current stock quantity of an item in a specific warehouse.
    """

    item = models.ForeignKey(
        Item, on_delete=models.CASCADE, related_name="stock_records"
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="stock_records"
    )
    quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["item", "warehouse"]
        permissions = [
            ("can_manage_stock", "Can manage stock"),
        ]
        ordering = ["item__item_code", "warehouse__name"]

    def __str__(self):
        return f"{self.item.name} at {self.warehouse.name}: {self.quantity}"

    def clean(self):
        if self.quantity < 0:
            raise ValidationError("Quantity cannot be negative.")


class StockMovement(models.Model):
    """
    Immutable history record for every stock movement.
    Stock balances are never silently edited; each change leaves a trace here.
    """

    MOVEMENT_TYPES = [
        ("Opening Stock", "Opening Stock"),
        ("Stock In", "Stock In"),
        ("Stock Out", "Stock Out"),
        ("Adjustment", "Stock Adjustment"),
        ("Transfer Out", "Stock Transfer Out"),
        ("Transfer In", "Stock Transfer In"),
        ("Purchase Receipt", "Purchase Receipt"),
        ("Sales Delivery", "Sales Delivery"),
        ("Return", "Return"),
    ]

    item = models.ForeignKey(
        Item, on_delete=models.CASCADE, related_name="stock_movements"
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="stock_movements"
    )
    quantity = models.IntegerField(
        help_text="Positive for stock in, negative for stock out."
    )
    balance_after = models.PositiveIntegerField(default=0)
    movement_type = models.CharField(max_length=50, choices=MOVEMENT_TYPES)
    reference_document = models.CharField(max_length=100, blank=True)
    reference_number = models.CharField(max_length=50, blank=True)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.movement_type}: {self.item} {self.quantity:+d} @ {self.warehouse}"


class StockTransfer(models.Model):
    """
    Transfer of stock from one warehouse to another.
    """

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Pending", "Pending Approval"),
        ("Approved", "Approved"),
        ("In Transit", "In Transit"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
        ("Rejected", "Rejected"),
    ]

    transfer_number = models.CharField(max_length=30, unique=True, blank=True)
    item = models.ForeignKey(
        Item, on_delete=models.CASCADE, related_name="transfers"
    )
    from_warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="transfers_from"
    )
    to_warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE, related_name="transfers_to"
    )
    quantity = models.PositiveIntegerField()
    transfer_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="Pending")
    notes = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transfers_requested",
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transfers_approved",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.transfer_number

    def clean(self):
        if self.from_warehouse == self.to_warehouse:
            raise ValidationError(
                "Source and destination warehouses cannot be the same."
            )
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than 0.")

    def save(self, *args, **kwargs):
        if not self.transfer_number:
            from accounts.models import DocumentSequence

            DocumentSequence.objects.get_or_create(
                document_type="ST",
                defaults={"prefix": "ST", "include_year": True},
            )
            self.transfer_number = DocumentSequence.get_next("ST")
        super().save(*args, **kwargs)