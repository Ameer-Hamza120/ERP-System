from django.contrib import admin
from .models import ItemGroup, Item, Warehouse, Stock, StockMovement, StockTransfer

admin.site.register(ItemGroup)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("item_code", "name", "sku", "group", "selling_price", "is_active")
    search_fields = ("item_code", "name", "sku", "barcode")


admin.site.register(Warehouse)
admin.site.register(Stock)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "movement_type",
        "item",
        "warehouse",
        "quantity",
        "balance_after",
        "reference_number",
        "user",
    )
    list_filter = ("movement_type", "warehouse")
    search_fields = ("item__item_code", "item__name", "reference_number")
    readonly_fields = (
        "item",
        "warehouse",
        "quantity",
        "balance_after",
        "movement_type",
        "reference_document",
        "reference_number",
        "user",
        "reason",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(StockTransfer)
