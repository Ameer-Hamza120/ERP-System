from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from inventory.models import ItemGroup, Item, Warehouse, Stock
from accounts.models import DocumentSequence

from .models import (
    Supplier, PurchaseRequest, PurchaseQuotation, PurchaseOrder,
    GoodsReceipt, APInvoice, OutgoingPayment,
)


class PurchasingFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="admin", password="adminpass123")
        self.client.login(username="admin", password="adminpass123")

        for doc_type in ["PR", "PQ", "PO", "GR", "APINV", "OP"]:
            DocumentSequence.objects.get_or_create(
                document_type=doc_type, defaults={"prefix": doc_type}
            )
        DocumentSequence.objects.get_or_create(
            document_type="SUPP", defaults={"prefix": "SUP", "include_year": False}
        )

        self.group = ItemGroup.objects.create(name="Parts")
        self.item = Item.objects.create(
            item_code="ITM-002", name="Chip", group=self.group,
            selling_price=300, purchase_price=250,
        )
        self.warehouse = Warehouse.objects.create(code="WH-002", name="Main")
        Stock.objects.create(item=self.item, warehouse=self.warehouse, quantity=50)

    def test_request_through_payment_flow(self):
        # Supplier
        self.client.post(reverse("supplier_create"), {"name": "Parts Supplier", "is_active": True})
        supplier = Supplier.objects.get(name="Parts Supplier")
        self.assertTrue(supplier.supplier_code.startswith("SUP-"))

        # Purchase Request
        response = self.client.post(
            reverse("purchaserequest_create"),
            {
                "requested_by_name": "IT", "department": "IT", "request_date": "2026-09-02",
                "lines-TOTAL_FORMS": "1", "lines-INITIAL_FORMS": "0",
                "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
                "lines-0-item": self.item.id, "lines-0-quantity": "10",
                "lines-0-unit_price": "250", "lines-0-discount_percent": "0",
                "lines-0-tax_percent": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        pr = PurchaseRequest.objects.first()
        self.assertTrue(pr.request_number.startswith("PR-"))
        self.client.get(reverse("purchaserequest_approve", args=[pr.pk]))
        pr.refresh_from_db()
        self.assertEqual(pr.status, "Approved")

        # Purchase Quotation
        response = self.client.post(
            f"{reverse('purchasequotation_create')}?request={pr.pk}",
            {
                "supplier": supplier.id, "request": pr.id, "quotation_date": "2026-09-02",
                "lines-TOTAL_FORMS": "1", "lines-INITIAL_FORMS": "0",
                "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
                "lines-0-item": self.item.id, "lines-0-quantity": "10",
                "lines-0-unit_price": "250", "lines-0-discount_percent": "0",
                "lines-0-tax_percent": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        pq = PurchaseQuotation.objects.first()
        self.client.get(reverse("purchasequotation_accept", args=[pq.pk]))
        pq.refresh_from_db()
        self.assertEqual(pq.status, "Accepted")

        # Purchase Order
        response = self.client.post(
            f"{reverse('purchaseorder_create')}?quotation={pq.pk}",
            {
                "supplier": supplier.id, "quotation": pq.id, "warehouse": self.warehouse.id,
                "order_date": "2026-09-02",
                "lines-TOTAL_FORMS": "1", "lines-INITIAL_FORMS": "0",
                "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
                "lines-0-item": self.item.id, "lines-0-quantity": "10",
                "lines-0-unit_price": "250", "lines-0-discount_percent": "0",
                "lines-0-tax_percent": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        po = PurchaseOrder.objects.first()
        self.assertTrue(po.order_number.startswith("PO-"))

        # Goods Receipt -> stock increases
        response = self.client.post(
            f"{reverse('goodsreceipt_create')}?order={po.pk}",
            {
                "supplier": supplier.id, "order": po.id, "warehouse": self.warehouse.id,
                "receipt_date": "2026-09-05",
                "lines-TOTAL_FORMS": "1", "lines-INITIAL_FORMS": "0",
                "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
                "lines-0-item": self.item.id, "lines-0-quantity": "10",
                "lines-0-unit_price": "250", "lines-0-discount_percent": "0",
                "lines-0-tax_percent": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        gr = GoodsReceipt.objects.first()
        self.client.get(reverse("goodsreceipt_post", args=[gr.pk]))
        gr.refresh_from_db()
        self.assertEqual(gr.status, "Posted")
        self.assertEqual(Stock.objects.get(item=self.item, warehouse=self.warehouse).quantity, 60)

        # A/P Invoice
        response = self.client.post(
            f"{reverse('apinvoice_create')}?receipt={gr.pk}",
            {
                "supplier": supplier.id, "goods_receipt": gr.id, "invoice_date": "2026-09-05",
                "lines-TOTAL_FORMS": "1", "lines-INITIAL_FORMS": "0",
                "lines-MIN_NUM_FORMS": "0", "lines-MAX_NUM_FORMS": "1000",
                "lines-0-item": self.item.id, "lines-0-quantity": "10",
                "lines-0-unit_price": "250", "lines-0-discount_percent": "0",
                "lines-0-tax_percent": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        inv = APInvoice.objects.first()
        self.assertEqual(inv.total, 2500)
        self.assertEqual(supplier.payable, 2500)

        # Outgoing Payment
        response = self.client.post(
            f"{reverse('outgoingpayment_create')}?invoice={inv.pk}",
            {
                "supplier": supplier.id, "invoice": inv.id, "payment_date": "2026-09-06",
                "amount": "2500", "payment_method": "Bank Transfer",
            },
        )
        self.assertEqual(response.status_code, 302)
        op = OutgoingPayment.objects.first()
        self.client.get(reverse("outgoingpayment_complete", args=[op.pk]))
        inv.refresh_from_db()
        self.assertEqual(inv.status, "Paid")
        self.assertEqual(supplier.payable, 0)
