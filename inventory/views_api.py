import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Sum

from audit.log import log_activity

from .models import Item, Warehouse, Stock, StockMovement, StockTransfer
from .forms import ItemForm, StockTransferForm


@require_http_methods(["GET", "POST"])
@login_required
def api_items(request):
    if request.method == "GET":
        if not request.user.has_perm("inventory.view_item"):
            return JsonResponse({"error": "Permission denied"}, status=403)
        items = Item.objects.annotate(
            total_stock=Sum("stock_records__quantity")
        ).values("id", "item_code", "name", "sku", "total_stock")
        return JsonResponse(list(items), safe=False)

    elif request.method == "POST":
        if not request.user.has_perm("inventory.add_item"):
            return JsonResponse({"error": "Permission denied"}, status=403)
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        form = ItemForm(data)
        if form.is_valid():
            item = form.save()
            log_activity(
                request.user,
                "Create Item",
                app_label="inventory",
                model_name="Item",
                object_id=item.pk,
                object_repr=item.item_code,
                new_values={"item_code": item.item_code, "name": item.name},
                request=request,
            )
            return JsonResponse(
                {"id": item.id, "item_code": item.item_code}, status=201
            )
        return JsonResponse({"errors": form.errors}, status=400)


@require_http_methods(["GET", "PUT", "DELETE"])
@login_required
def api_item_detail(request, pk):
    try:
        item = Item.objects.get(pk=pk)
    except Item.DoesNotExist:
        return JsonResponse({"error": "Item not found"}, status=404)

    if request.method == "GET":
        if not request.user.has_perm("inventory.view_item"):
            return JsonResponse({"error": "Permission denied"}, status=403)
        data = {
            "id": item.id,
            "item_code": item.item_code,
            "name": item.name,
            "sku": item.sku,
            "group": item.group.name if item.group else None,
            "current_stock": item.current_stock,
        }
        return JsonResponse(data)

    elif request.method == "PUT":
        if not request.user.has_perm("inventory.change_item"):
            return JsonResponse({"error": "Permission denied"}, status=403)
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        form = ItemForm(data, instance=item)
        if form.is_valid():
            item = form.save()
            log_activity(
                request.user,
                "Update Item",
                app_label="inventory",
                model_name="Item",
                object_id=item.pk,
                object_repr=item.item_code,
                new_values={"name": item.name},
                request=request,
            )
            return JsonResponse({"id": item.id, "item_code": item.item_code})
        return JsonResponse({"errors": form.errors}, status=400)

    elif request.method == "DELETE":
        if not request.user.has_perm("inventory.delete_item"):
            return JsonResponse({"error": "Permission denied"}, status=403)
        log_activity(
            request.user,
            "Delete Item",
            app_label="inventory",
            model_name="Item",
            object_id=item.pk,
            object_repr=item.item_code,
            request=request,
        )
        item.delete()
        return JsonResponse({"success": True})


@require_http_methods(["GET"])
@login_required
def api_warehouses(request):
    if not request.user.has_perm("inventory.view_warehouse"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    warehouses = Warehouse.objects.values(
        "id", "code", "name", "location", "is_active"
    )
    return JsonResponse(list(warehouses), safe=False)


@require_http_methods(["GET"])
@login_required
def api_stock(request):
    if not request.user.has_perm("inventory.view_stock"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    stocks = Stock.objects.select_related("item", "warehouse").values(
        "id", "item__name", "item__item_code", "warehouse__name", "quantity"
    )
    return JsonResponse(list(stocks), safe=False)


@require_http_methods(["GET"])
@login_required
def api_stock_movements(request):
    if not request.user.has_perm("inventory.view_stock"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    item_id = request.GET.get("item")
    warehouse_id = request.GET.get("warehouse")
    movements = StockMovement.objects.select_related("item", "warehouse", "user").order_by("-created_at")
    if item_id:
        movements = movements.filter(item_id=item_id)
    if warehouse_id:
        movements = movements.filter(warehouse_id=warehouse_id)
    data = movements[:200].values(
        "id",
        "created_at",
        "item__item_code",
        "item__name",
        "warehouse__name",
        "quantity",
        "balance_after",
        "movement_type",
        "reference_number",
        "user__username",
        "reason",
    )
    return JsonResponse(list(data), safe=False)


@require_http_methods(["GET", "POST"])
@login_required
def api_transfers(request):
    if request.method == "GET":
        if not request.user.has_perm("inventory.view_stocktransfer"):
            return JsonResponse({"error": "Permission denied"}, status=403)
        transfers = StockTransfer.objects.select_related(
            "item", "from_warehouse", "to_warehouse"
        ).values(
            "id",
            "transfer_number",
            "item__name",
            "from_warehouse__name",
            "to_warehouse__name",
            "quantity",
            "status",
        )
        return JsonResponse(list(transfers), safe=False)

    elif request.method == "POST":
        if not request.user.has_perm("inventory.add_stocktransfer"):
            return JsonResponse({"error": "Permission denied"}, status=403)
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        form = StockTransferForm(data)
        if form.is_valid():
            transfer = form.save(commit=False)
            transfer.requested_by = request.user
            transfer.status = "Pending"
            transfer.save()
            log_activity(
                request.user,
                "Create Stock Transfer",
                app_label="inventory",
                model_name="StockTransfer",
                object_id=transfer.pk,
                object_repr=transfer.transfer_number,
                new_values={"transfer_number": transfer.transfer_number},
                request=request,
            )
            return JsonResponse(
                {"id": transfer.id, "transfer_number": transfer.transfer_number},
                status=201,
            )
        return JsonResponse({"errors": form.errors}, status=400)