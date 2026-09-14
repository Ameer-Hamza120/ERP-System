from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User


class Command(BaseCommand):
    help = "Create default roles, permissions, and document sequences"

    def handle(self, *args, **kwargs):
        from accounts.models import DocumentSequence

        # ---------------- Roles ----------------
        admin_group, _ = Group.objects.get_or_create(name="Super Admin")
        manager_group, _ = Group.objects.get_or_create(name="Manager")
        employee_group, _ = Group.objects.get_or_create(name="Employee")
        inv_manager_group, _ = Group.objects.get_or_create(name="Inventory Manager")
        inv_staff_group, _ = Group.objects.get_or_create(name="Inventory Employee")

        # Super Admin gets every permission
        admin_group.permissions.clear()
        admin_group.permissions.set(Permission.objects.all())

        # Manager: view users, full inventory management + sales + purchasing
        manager_permissions = [
            "view_user",
            "view_itemgroup", "add_itemgroup", "change_itemgroup", "delete_itemgroup",
            "view_item", "add_item", "change_item", "delete_item",
            "view_warehouse", "add_warehouse", "change_warehouse", "delete_warehouse",
            "view_stock", "can_manage_stock",
            "view_stocktransfer", "add_stocktransfer", "change_stocktransfer",
            # Sales
            "view_customer", "add_customer", "change_customer", "delete_customer",
            "view_salesquotation", "add_salesquotation", "change_salesquotation", "delete_salesquotation",
            "view_salesorder", "add_salesorder", "change_salesorder", "delete_salesorder",
            "view_delivery", "add_delivery", "change_delivery", "delete_delivery",
            "view_returnrequest", "add_returnrequest", "change_returnrequest", "delete_returnrequest",
            "view_salesreturn", "add_salesreturn", "change_salesreturn", "delete_salesreturn",
            "view_arinvoice", "add_arinvoice", "change_arinvoice", "delete_arinvoice",
            "view_arcreditmemo", "add_arcreditmemo", "change_arcreditmemo", "delete_arcreditmemo",
            "view_incomingpayment", "add_incomingpayment", "change_incomingpayment", "delete_incomingpayment",
            # Purchasing
            "view_supplier", "add_supplier", "change_supplier", "delete_supplier",
            "view_purchaserequest", "add_purchaserequest", "change_purchaserequest", "delete_purchaserequest",
            "view_purchasequotation", "add_purchasequotation", "change_purchasequotation", "delete_purchasequotation",
            "view_purchaseorder", "add_purchaseorder", "change_purchaseorder", "delete_purchaseorder",
            "view_goodsreceipt", "add_goodsreceipt", "change_goodsreceipt", "delete_goodsreceipt",
            "view_apinvoice", "add_apinvoice", "change_apinvoice", "delete_apinvoice",
            "view_apcreditmemo", "add_apcreditmemo", "change_apcreditmemo", "delete_apcreditmemo",
            "view_outgoingpayment", "add_outgoingpayment", "change_outgoingpayment", "delete_outgoingpayment",
        ]
        manager_group.permissions.clear()
        for codename in manager_permissions:
            perm = Permission.objects.filter(codename=codename).first()
            if perm:
                manager_group.permissions.add(perm)

        # Employee: read-only visibility of inventory
        employee_permissions = [
            "view_itemgroup",
            "view_item",
            "view_warehouse",
            "view_stock",
            "view_stocktransfer",
        ]
        employee_group.permissions.clear()
        for codename in employee_permissions:
            perm = Permission.objects.filter(codename=codename).first()
            if perm:
                employee_group.permissions.add(perm)

        # Inventory Manager
        inv_manager_group.permissions.clear()
        for codename in manager_permissions:
            perm = Permission.objects.filter(codename=codename).first()
            if perm:
                inv_manager_group.permissions.add(perm)

        # Inventory Employee
        inv_staff_permissions = [
            "view_itemgroup",
            "view_item",
            "view_warehouse",
            "view_stock",
            "view_stocktransfer",
            "add_stocktransfer",
        ]
        inv_staff_group.permissions.clear()
        for codename in inv_staff_permissions:
            perm = Permission.objects.filter(codename=codename).first()
            if perm:
                inv_staff_group.permissions.add(perm)

        # Sales Manager: full sales management
        sales_manager_group, _ = Group.objects.get_or_create(name="Sales Manager")
        sales_permissions = [
            "view_customer", "add_customer", "change_customer", "delete_customer",
            "view_salesquotation", "add_salesquotation", "change_salesquotation", "delete_salesquotation",
            "view_salesorder", "add_salesorder", "change_salesorder", "delete_salesorder",
            "view_delivery", "add_delivery", "change_delivery", "delete_delivery",
            "view_returnrequest", "add_returnrequest", "change_returnrequest", "delete_returnrequest",
            "view_salesreturn", "add_salesreturn", "change_salesreturn", "delete_salesreturn",
            "view_arinvoice", "add_arinvoice", "change_arinvoice", "delete_arinvoice",
            "view_arcreditmemo", "add_arcreditmemo", "change_arcreditmemo", "delete_arcreditmemo",
            "view_incomingpayment", "add_incomingpayment", "change_incomingpayment", "delete_incomingpayment",
        ]
        sales_manager_group.permissions.clear()
        for codename in sales_permissions:
            perm = Permission.objects.filter(codename=codename).first()
            if perm:
                sales_manager_group.permissions.add(perm)

        # Purchasing Manager: full purchasing management
        purchasing_manager_group, _ = Group.objects.get_or_create(name="Purchasing Manager")
        purchasing_permissions = [
            "view_supplier", "add_supplier", "change_supplier", "delete_supplier",
            "view_purchaserequest", "add_purchaserequest", "change_purchaserequest", "delete_purchaserequest",
            "view_purchasequotation", "add_purchasequotation", "change_purchasequotation", "delete_purchasequotation",
            "view_purchaseorder", "add_purchaseorder", "change_purchaseorder", "delete_purchaseorder",
            "view_goodsreceipt", "add_goodsreceipt", "change_goodsreceipt", "delete_goodsreceipt",
            "view_apinvoice", "add_apinvoice", "change_apinvoice", "delete_apinvoice",
            "view_apcreditmemo", "add_apcreditmemo", "change_apcreditmemo", "delete_apcreditmemo",
            "view_outgoingpayment", "add_outgoingpayment", "change_outgoingpayment", "delete_outgoingpayment",
        ]
        purchasing_manager_group.permissions.clear()
        for codename in purchasing_permissions:
            perm = Permission.objects.filter(codename=codename).first()
            if perm:
                purchasing_manager_group.permissions.add(perm)

        # ---------------- Document Sequences ----------------
        default_sequences = [
            {"document_type": "SO", "prefix": "SO"},
            {"document_type": "PO", "prefix": "PO"},
            {"document_type": "INV", "prefix": "INV"},
            {"document_type": "GR", "prefix": "GR"},
            {"document_type": "ST", "prefix": "ST"},
            {"document_type": "ITEM", "prefix": "ITM", "include_year": False},
            # Sales (A/R)
            {"document_type": "CUST", "prefix": "CUS", "include_year": False},
            {"document_type": "SQ", "prefix": "SQ"},
            {"document_type": "DLV", "prefix": "DLV"},
            {"document_type": "RR", "prefix": "RR"},
            {"document_type": "RTN", "prefix": "RTN"},
            {"document_type": "CRM", "prefix": "CRM"},
            {"document_type": "IP", "prefix": "IP"},
            # Purchasing (A/P)
            {"document_type": "SUPP", "prefix": "SUP", "include_year": False},
            {"document_type": "PR", "prefix": "PR"},
            {"document_type": "PQ", "prefix": "PQ"},
            {"document_type": "APINV", "prefix": "APINV"},
            {"document_type": "APCRM", "prefix": "APCRM"},
            {"document_type": "OP", "prefix": "OP"},
        ]
        for seq in default_sequences:
            DocumentSequence.objects.get_or_create(
                document_type=seq["document_type"],
                defaults={
                    "prefix": seq["prefix"],
                    "include_year": seq.get("include_year", True),
                },
            )

        # ---------------- Assign superusers ----------------
        for user in User.objects.filter(is_superuser=True):
            user.groups.clear()
            user.groups.add(admin_group)

        self.stdout.write(
            self.style.SUCCESS(
                "Roles, permissions, and document sequences set up successfully."
            )
        )
        self.stdout.write("Default roles: Super Admin, Manager, Employee, Inventory Manager, Inventory Employee, Sales Manager, Purchasing Manager")