from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from inventory.models import ItemGroup, Item, Warehouse, Stock
from accounts.models import DocumentSequence

from .models import (
    Customer,
    SalesQuotation, SalesQuotationLine, SalesOrder, SalesOrderLine,
    Delivery, DeliveryLine, ARInvoice, ARInvoiceLine, IncomingPayment,
)


class SalesFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="admin", password="adminpass123")
        self.client.login(username="admin", password="adminpass123")

        DocumentSequence.objects.get_or_create(
            document_type="SQ", defaults={"prefix": "SQ"}
        )
        DocumentSequence.objects.get_or_create(
            document_type="SO", defaults={"prefix": "SO"}
        )
        DocumentSequence.objects.get_or_create(
            document_type="DLV", defaults={"prefix": "DLV"}
        )
        DocumentSequence.objects.get_or_create(
            document_type="INV", defaults={"prefix": "INV"}
        )
        DocumentSequence.objects.get_or_create(
            document_type="IP", defaults={"prefix": "IP"}
        )
        DocumentSequence.objects.get_or_create(
            document_type="CUST", defaults={"prefix": "CUS", "include_year": False}
        )

        self.group = ItemGroup.objects.create(name="Electronics")
        self.item = Item.objects.create(
            item_code="ITM-001", name="Laptop", group=self.group,
            selling_price=300, purchase_price=250,
        )
        self.warehouse = Warehouse.objects.create(code="WH-001", name="Main")
        Stock.objects.create(item=self.item, warehouse=self.warehouse, quantity=100)

    def test_quotation_through_payment_flow(self):
        # Customer
        response = self.client.post(
            reverse("customer_create"),
            {"name": "Acme", "is_active": True},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        customer = Customer.objects.get(name="Acme")

        # Quotation
        response = self.client.post(
            reverse("salesquotation_create"),
            {
                "customer": customer.id,
                "quotation_date": "2026-09-02",
                "lines-TOTAL_FORMS": "1", "lines-INITIAL_FORMS": "0",
                "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
                "lines-0-item": self.item.id, "lines-0-quantity": "10",
                "lines-0-unit_price": "300", "lines-0-discount_percent": "0",
                "lines-0-tax_percent": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        quote = SalesQuotation.objects.get(customer=customer)
        self.assertTrue(quote.quotation_number.startswith("SQ-"))
        self.assertEqual(quote.lines.count(), 1)

        # Accept quotation
        self.client.get(reverse("salesquotation_accept", args=[quote.pk]))
        quote.refresh_from_db()
        self.assertEqual(quote.status, "Accepted")

        # Sales Order
        response = self.client.post(
            f"{reverse('salesorder_create')}?quotation={quote.pk}",
            {
                "customer": customer.id, "quotation": quote.id,
                "warehouse": self.warehouse.id, "order_date": "2026-09-02",
                "lines-TOTAL_FORMS": "1", "lines-INITIAL_FORMS": "0",
                "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
                "lines-0-item": self.item.id, "lines-0-quantity": "10",
                "lines-0-unit_price": "300", "lines-0-discount_percent": "0",
                "lines-0-tax_percent": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        order = SalesOrder.objects.get(customer=customer)
        self.assertEqual(order.lines.count(), 1)

        # Delivery
        response = self.client.post(
            f"{reverse('delivery_create')}?order={order.pk}",
            {
                "customer": customer.id, "order": order.id,
                "warehouse": self.warehouse.id, "delivery_date": "2026-09-02",
                "lines-TOTAL_FORMS": "1", "lines-INITIAL_FORMS": "0",
                "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
                "lines-0-item": self.item.id, "lines-0-quantity": "10",
                "lines-0-unit_price": "300", "lines-0-discount_percent": "0",
                "lines-0-tax_percent": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        delivery = Delivery.objects.get(customer=customer)

        # Post delivery -> stock decreases
        self.client.get(reverse("delivery_post", args=[delivery.pk]))
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, "Posted")
        self.assertEqual(Stock.objects.get(item=self.item, warehouse=self.warehouse).quantity, 90)

        # A/R Invoice
        response = self.client.post(
            f"{reverse('arinvoice_create')}?delivery={delivery.pk}",
            {
                "customer": customer.id, "delivery": delivery.id,
                "invoice_date": "2026-09-02",
                "lines-TOTAL_FORMS": "1", "lines-INITIAL_FORMS": "0",
                "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
                "lines-0-item": self.item.id, "lines-0-quantity": "10",
                "lines-0-unit_price": "300", "lines-0-discount_percent": "0",
                "lines-0-tax_percent": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        invoice = ARInvoice.objects.get(customer=customer)
        self.assertEqual(invoice.total, 3000)
        self.assertEqual(customer.receivable, 3000)

        # Incoming payment
        response = self.client.post(
            f"{reverse('incomingpayment_create')}?invoice={invoice.pk}",
            {
                "customer": customer.id, "invoice": invoice.id,
                "payment_date": "2026-09-03", "amount": "3000",
                "payment_method": "Bank Transfer",
            },
        )
        self.assertEqual(response.status_code, 302)
        payment = IncomingPayment.objects.get(customer=customer)
        self.client.get(reverse("incomingpayment_complete", args=[payment.pk]))
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "Paid")
        self.assertEqual(customer.receivable, 0)

    def test_customer_auto_code(self):
        self.client.post(reverse("customer_create"), {"name": "Test Co", "is_active": True})
        customer = Customer.objects.get(name="Test Co")
        self.assertTrue(customer.customer_code.startswith("CUS-"))
