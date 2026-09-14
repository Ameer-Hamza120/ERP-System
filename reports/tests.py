from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from inventory.models import ItemGroup, Item, Warehouse, Stock


class ReportsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="admin", password="adminpass123")
        self.client.login(username="admin", password="adminpass123")
        group = ItemGroup.objects.create(name="Reports Group")
        self.item = Item.objects.create(
            item_code="RPT-001", name="Report Item", group=group, minimum_stock_level=10,
        )
        self.warehouse = Warehouse.objects.create(code="RPT-WH", name="Reports Warehouse")
        Stock.objects.create(item=self.item, warehouse=self.warehouse, quantity=3)

    def test_inventory_report(self):
        self.assertEqual(self.client.get(reverse("inventory_report")).status_code, 200)

    def test_low_stock_report(self):
        response = self.client.get(reverse("low_stock_report"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RPT-001")

    def test_stock_transfer_report(self):
        self.assertEqual(self.client.get(reverse("stock_transfer_report")).status_code, 200)

    def test_csv_exports(self):
        for url_name in ("export_inventory_csv", "export_low_stock_csv", "export_transfer_csv"):
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "text/csv")
