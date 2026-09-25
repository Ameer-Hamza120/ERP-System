from django.test import TestCase
from django.contrib.auth.models import User
from django import forms
from django.urls import reverse
from .forms import ItemForm
from .models import ItemGroup, Item, Warehouse, Stock, StockMovement, StockTransfer


class InventoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin", password="adminpass123"
        )
        self.client.login(username="admin", password="adminpass123")

        self.group = ItemGroup.objects.create(name="Electronics")
        self.item = Item.objects.create(
            item_code="ITM-001",
            name="Keyboard",
            group=self.group,
            minimum_stock_level=10,
        )
        self.wh1 = Warehouse.objects.create(code="WH-001", name="Main Warehouse")
        self.wh2 = Warehouse.objects.create(code="WH-002", name="Branch Warehouse")

    def test_item_create(self):
        response = self.client.post(
            reverse("item_create"),
            {
                "name": "Mouse",
                "group": self.group.id,
                "unit_of_measure": "Piece",
                "purchase_price": 5,
                "selling_price": 8,
                "minimum_stock_level": 5,
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Item.objects.filter(name="Mouse").exists())
        item = Item.objects.get(name="Mouse")
        self.assertTrue(item.item_code.startswith("ITM-"))

    def test_item_create_with_current_stock(self):
        response = self.client.post(
            reverse("item_create"),
            {
                "name": "Monitor",
                "group": self.group.id,
                "unit_of_measure": "Piece",
                "purchase_price": 50,
                "selling_price": 75,
                "minimum_stock_level": 2,
                "current_stock": 12,
                "current_stock_warehouse": self.wh1.id,
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        item = Item.objects.get(name="Monitor")
        self.assertEqual(
            Stock.objects.get(item=item, warehouse=self.wh1).quantity,
            12,
        )
        self.assertTrue(
            StockMovement.objects.filter(
                item=item,
                warehouse=self.wh1,
                movement_type="Opening Stock",
                quantity=12,
            ).exists()
        )

    def test_item_form_uses_unit_of_measure_dropdown(self):
        field = ItemForm().fields["unit_of_measure"]

        self.assertIsInstance(field.widget, forms.Select)
        self.assertEqual(
            [value for value, _ in field.choices],
            [value for value, _ in Item.UNIT_OF_MEASURE_CHOICES],
        )

    def test_item_form_does_not_include_image(self):
        self.assertNotIn("image", ItemForm().fields)

    def test_existing_item_form_shows_current_stock_read_only(self):
        Stock.objects.create(item=self.item, warehouse=self.wh1, quantity=7)
        form = ItemForm(instance=self.item)
        self.assertIn("current_stock", form.fields)
        self.assertEqual(form.initial["current_stock"], 7)
        self.assertTrue(form.fields["current_stock"].disabled)
        self.assertNotIn("current_stock_warehouse", form.fields)

    def test_stock_in(self):
        response = self.client.post(
            reverse("stock_in"),
            {"item": self.item.id, "warehouse": self.wh1.id, "quantity": 20},
        )
        self.assertEqual(response.status_code, 302)
        stock = Stock.objects.get(item=self.item, warehouse=self.wh1)
        self.assertEqual(stock.quantity, 20)

    def test_stock_out(self):
        Stock.objects.create(item=self.item, warehouse=self.wh1, quantity=30)
        response = self.client.post(
            reverse("stock_out"),
            {"item": self.item.id, "warehouse": self.wh1.id, "quantity": 10},
        )
        self.assertEqual(response.status_code, 302)
        stock = Stock.objects.get(item=self.item, warehouse=self.wh1)
        self.assertEqual(stock.quantity, 20)

    def test_stock_out_insufficient(self):
        Stock.objects.create(item=self.item, warehouse=self.wh1, quantity=5)
        response = self.client.post(
            reverse("stock_out"),
            {"item": self.item.id, "warehouse": self.wh1.id, "quantity": 10},
        )
        self.assertEqual(response.status_code, 200)
        stock = Stock.objects.get(item=self.item, warehouse=self.wh1)
        self.assertEqual(stock.quantity, 5)  # unchanged

    def test_stock_transfer(self):
        Stock.objects.create(item=self.item, warehouse=self.wh1, quantity=50)
        transfer = StockTransfer.objects.create(
            item=self.item,
            from_warehouse=self.wh1,
            to_warehouse=self.wh2,
            quantity=20,
            requested_by=self.user,
        )
        response = self.client.get(
            reverse("stocktransfer_complete", args=[transfer.pk])
        )
        self.assertEqual(response.status_code, 302)
        source_stock = Stock.objects.get(item=self.item, warehouse=self.wh1)
        dest_stock = Stock.objects.get(item=self.item, warehouse=self.wh2)
        self.assertEqual(source_stock.quantity, 30)
        self.assertEqual(dest_stock.quantity, 20)

    def test_stock_transfer_insufficient(self):
        Stock.objects.create(item=self.item, warehouse=self.wh1, quantity=5)
        transfer = StockTransfer.objects.create(
            item=self.item,
            from_warehouse=self.wh1,
            to_warehouse=self.wh2,
            quantity=20,
            requested_by=self.user,
        )
        response = self.client.get(
            reverse("stocktransfer_complete", args=[transfer.pk])
        )
        self.assertEqual(response.status_code, 302)
        transfer.refresh_from_db()
        self.assertEqual(transfer.status, "Pending")

    def test_item_update(self):
        response = self.client.post(
            reverse("item_update", args=[self.item.pk]),
            {
                "item_code": "ITM-001",
                "name": "Wireless Keyboard",
                "group": self.group.id,
                "unit_of_measure": "Piece",
                "purchase_price": 6,
                "selling_price": 10,
                "minimum_stock_level": 10,
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.name, "Wireless Keyboard")

    def test_item_delete(self):
        response = self.client.post(reverse("item_delete", args=[self.item.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Item.objects.filter(pk=self.item.pk).exists())

    def test_warehouse_create(self):
        response = self.client.post(
            reverse("warehouse_create"),
            {
                "code": "WH-003",
                "name": "New Warehouse",
                "location": "Muscat",
                "description": "",
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Warehouse.objects.filter(code="WH-003").exists())

    def test_low_stock_calculation(self):
        Stock.objects.create(item=self.item, warehouse=self.wh1, quantity=5)
        self.assertEqual(self.item.current_stock, 5)
        self.assertLessEqual(self.item.current_stock, self.item.minimum_stock_level)

    def test_inventory_report(self):
        Stock.objects.create(item=self.item, warehouse=self.wh1, quantity=10)
        response = self.client.get(reverse("inventory_report"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ITM-001")

    def test_low_stock_report(self):
        Stock.objects.create(item=self.item, warehouse=self.wh1, quantity=3)
        response = self.client.get(reverse("low_stock_report"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ITM-001")


class StockMovementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin", password="adminpass123"
        )
        self.client.login(username="admin", password="adminpass123")
        self.group = ItemGroup.objects.create(name="Electronics")
        self.item = Item.objects.create(
            item_code="ITM-100",
            name="Monitor",
            group=self.group,
            minimum_stock_level=10,
        )
        self.wh1 = Warehouse.objects.create(code="WH-100", name="Main Warehouse")
        self.wh2 = Warehouse.objects.create(code="WH-200", name="Branch Warehouse")

    def test_stock_in_creates_movement(self):
        self.client.post(
            reverse("stock_in"),
            {"item": self.item.id, "warehouse": self.wh1.id, "quantity": 20},
        )
        movement = StockMovement.objects.get(item=self.item, warehouse=self.wh1)
        self.assertEqual(movement.movement_type, "Stock In")
        self.assertEqual(movement.quantity, 20)
        self.assertEqual(movement.balance_after, 20)

    def test_stock_out_creates_movement(self):
        Stock.objects.create(item=self.item, warehouse=self.wh1, quantity=30)
        self.client.post(
            reverse("stock_out"),
            {"item": self.item.id, "warehouse": self.wh1.id, "quantity": 10},
        )
        movement = StockMovement.objects.get(
            item=self.item, warehouse=self.wh1, movement_type="Stock Out"
        )
        self.assertEqual(movement.quantity, -10)
        self.assertEqual(movement.balance_after, 20)

    def test_transfer_creates_two_movements(self):
        from accounts.models import DocumentSequence

        DocumentSequence.objects.get_or_create(
            document_type="ST", defaults={"prefix": "ST"}
        )
        Stock.objects.create(item=self.item, warehouse=self.wh1, quantity=50)
        transfer = StockTransfer.objects.create(
            item=self.item,
            from_warehouse=self.wh1,
            to_warehouse=self.wh2,
            quantity=20,
            requested_by=self.user,
        )
        self.client.get(reverse("stocktransfer_complete", args=[transfer.pk]))
        movements = StockMovement.objects.filter(
            item=self.item, reference_number=transfer.transfer_number
        )
        self.assertEqual(movements.count(), 2)
        types = sorted(movements.values_list("movement_type", flat=True))
        self.assertEqual(types, ["Transfer In", "Transfer Out"])

    def test_transfer_uses_sequence_number(self):
        from accounts.models import DocumentSequence

        seq, _ = DocumentSequence.objects.get_or_create(
            document_type="ST", defaults={"prefix": "ST", "include_year": True}
        )
        seq.next_number = 1
        seq.save(update_fields=["next_number"])
        t1 = StockTransfer.objects.create(
            item=self.item,
            from_warehouse=self.wh1,
            to_warehouse=self.wh2,
            quantity=1,
            requested_by=self.user,
        )
        t2 = StockTransfer.objects.create(
            item=self.item,
            from_warehouse=self.wh1,
            to_warehouse=self.wh2,
            quantity=2,
            requested_by=self.user,
        )
        self.assertNotEqual(t1.transfer_number, t2.transfer_number)
        self.assertTrue(t1.transfer_number.startswith("ST-"))
        seq.refresh_from_db()
        self.assertEqual(seq.next_number, 3)

    def test_transfer_audit_logged(self):
        from audit.models import AuditLog
        from accounts.models import DocumentSequence

        DocumentSequence.objects.get_or_create(
            document_type="ST", defaults={"prefix": "ST"}
        )
        Stock.objects.create(item=self.item, warehouse=self.wh1, quantity=50)
        transfer = StockTransfer.objects.create(
            item=self.item,
            from_warehouse=self.wh1,
            to_warehouse=self.wh2,
            quantity=20,
            requested_by=self.user,
        )
        self.client.get(reverse("stocktransfer_complete", args=[transfer.pk]))
        self.assertTrue(
            AuditLog.objects.filter(action="Complete Stock Transfer").exists()
        )