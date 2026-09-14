from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone


def get_next_document_number(document_type, prefix, include_year=True):
    seq, _ = DocumentSequence.objects.get_or_create(
        document_type=document_type,
        defaults={"prefix": prefix, "include_year": include_year},
    )
    return DocumentSequence.get_next(document_type)


class CompanySettings(models.Model):
    """
    Stores company-wide settings. Only one row is used in the entire system.
    """

    company_name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    tax_id = models.CharField("Tax/VAT ID", max_length=100, blank=True)
    currency = models.CharField("Base Currency", max_length=10, default="USD")
    fiscal_year_start = models.DateField(null=True, blank=True)
    fiscal_year_end = models.DateField(null=True, blank=True)
    date_format = models.CharField(max_length=20, default="Y-m-d")
    timezone = models.CharField(max_length=50, default="UTC")
    default_warehouse = models.ForeignKey(
        "inventory.Warehouse",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    default_payment_terms = models.CharField(max_length=100, blank=True)
    invoice_terms = models.TextField(blank=True)
    logo = models.ImageField(upload_to="company_logos/", blank=True, null=True)

    def clean(self):
        if self.fiscal_year_start and self.fiscal_year_end:
            if self.fiscal_year_end <= self.fiscal_year_start:
                raise ValidationError(
                    "Fiscal year end must be after fiscal year start."
                )

    def __str__(self):
        return self.company_name


class DocumentSequence(models.Model):
    """
    Numbering sequence for ERP documents (SO, PO, INV, GR, ST, ...).
    Each document type has a unique sequence to prevent duplicate numbers.
    """

    document_type = models.CharField(max_length=20, unique=True)
    prefix = models.CharField(max_length=10)
    include_year = models.BooleanField(default=True)
    next_number = models.PositiveBigIntegerField(default=1)
    padding = models.PositiveSmallIntegerField(default=6)
    last_number = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["document_type"]

    def __str__(self):
        return f"{self.document_type} ({self.prefix})"

    def clean(self):
        if self.padding < 1:
            raise ValidationError("Padding must be at least 1.")

    @classmethod
    def get_next(cls, document_type, prefix=None, include_year=None):
        """
        Atomically fetch and increment the next document number for a type.

        Returns a number string such as "ST-2026-000001". The sequence row is
        locked with select_for_update so concurrent requests never collide.
        """
        from django.utils import timezone

        with transaction.atomic():
            seq = cls.objects.select_for_update().get(document_type=document_type)
            if prefix:
                seq.prefix = prefix
            if include_year is not None:
                seq.include_year = include_year

            year = timezone.now().year if seq.include_year else None
            number = seq.next_number
            padded = str(number).zfill(seq.padding)

            if year is not None:
                result = f"{seq.prefix}-{year}-{padded}"
            else:
                result = f"{seq.prefix}-{padded}"

            seq.next_number += 1
            seq.last_number = result
            seq.save(update_fields=["prefix", "include_year", "next_number", "last_number"])
            return result