from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404

from audit.log import log_activity

from .forms import (
    ItemGroupForm,
    ItemForm,
    WarehouseForm,
    StockInForm,
    StockOutForm,
    StockTransferForm,
)
from .models import ItemGroup, Item, Warehouse, Stock, StockMovement, StockTransfer
from common.utils import (
    model_values as _model_values,
    get_or_none as _get_or_none,
    list_context as _list_context,
    action_url as _action_url,
)
from inventory.services import record_stock_movement as _record_stock_movement


# ---------------- Item Groups ----------------

@permission_required("inventory.view_itemgroup", raise_exception=True)
def itemgroup_list(request):
    query = request.GET.get("q", "")
    groups = ItemGroup.objects.all().order_by("name")
    if query:
        groups = groups.filter(name__icontains=query)
    paginator = Paginator(groups, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "inventory/itemgroup_list.html",
        {"page_obj": page_obj, "query": query},
    )


@permission_required("inventory.add_itemgroup", raise_exception=True)
def itemgroup_create(request):
    if request.method == "POST":
        form = ItemGroupForm(request.POST)
        if form.is_valid():
            obj = form.save()
            log_activity(
                request.user,
                "Create Item Group",
                app_label="inventory",
                model_name="ItemGroup",
                object_id=obj.pk,
                object_repr=obj.name,
                new_values=_model_values(obj),
                request=request,
            )
            messages.success(request, "Item group added successfully.")
            return redirect("itemgroup_list")
    else:
        form = ItemGroupForm()
    return render(
        request,
        "inventory/itemgroup_form.html",
        {"form": form, "title": "Add Item Group"},
    )


@permission_required("inventory.change_itemgroup", raise_exception=True)
def itemgroup_update(request, pk):
    group = get_object_or_404(ItemGroup, pk=pk)
    old = _model_values(group)
    if request.method == "POST":
        form = ItemGroupForm(request.POST, instance=group)
        if form.is_valid():
            obj = form.save()
            log_activity(
                request.user,
                "Update Item Group",
                app_label="inventory",
                model_name="ItemGroup",
                object_id=obj.pk,
                object_repr=obj.name,
                old_values=old,
                new_values=_model_values(obj),
                request=request,
            )
            messages.success(request, "Item group updated successfully.")
            return redirect("itemgroup_list")
    else:
        form = ItemGroupForm(instance=group)
    return render(
        request,
        "inventory/itemgroup_form.html",
        {"form": form, "title": f"Edit Item Group: {group.name}"},
    )


@permission_required("inventory.delete_itemgroup", raise_exception=True)
def itemgroup_delete(request, pk):
    group = get_object_or_404(ItemGroup, pk=pk)
    if request.method == "POST":
        log_activity(
            request.user,
            "Delete Item Group",
            app_label="inventory",
            model_name="ItemGroup",
            object_id=group.pk,
            object_repr=group.name,
            request=request,
        )
        group.delete()
        messages.success(request, "Item group deleted successfully.")
        return redirect("itemgroup_list")
    return render(
        request,
        "inventory/itemgroup_confirm_delete.html",
        {"group": group},
    )


# ---------------- Items ----------------

@permission_required("inventory.view_item", raise_exception=True)
def item_list(request):
    query = request.GET.get("q", "")
    group_id = request.GET.get("group", "")
    items = (
        Item.objects.select_related("group")
        .annotate(total_stock=Sum("stock_records__quantity"))
        .order_by("item_code")
    )

    if query:
        items = items.filter(
            Q(item_code__icontains=query) | Q(name__icontains=query)
        )
    if group_id:
        items = items.filter(group_id=group_id)

    groups = ItemGroup.objects.filter(is_active=True).order_by("name")
    paginator = Paginator(items, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "inventory/item_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "group_id": group_id,
            "groups": groups,
        },
    )


@permission_required("inventory.view_item", raise_exception=True)
def item_detail(request, pk):
    item = get_object_or_404(Item.objects.select_related("group"), pk=pk)
    stocks = Stock.objects.filter(item=item).select_related("warehouse")
    return render(
        request, "inventory/item_detail.html", {"item": item, "stocks": stocks}
    )


@permission_required("inventory.add_item", raise_exception=True)
def item_create(request):
    if request.method == "POST":
        form = ItemForm(request.POST)
        if form.is_valid():
            current_stock = form.cleaned_data.get("current_stock") or 0
            warehouse = form.cleaned_data.get("current_stock_warehouse")
            with transaction.atomic():
                obj = form.save()
                if current_stock:
                    stock = Stock.objects.create(
                        item=obj,
                        warehouse=warehouse,
                        quantity=current_stock,
                    )
                    _record_stock_movement(
                        obj,
                        warehouse,
                        current_stock,
                        "Opening Stock",
                        request.user,
                        stock.quantity,
                    )
            log_activity(
                request.user,
                "Create Item",
                app_label="inventory",
                model_name="Item",
                object_id=obj.pk,
                object_repr=obj.item_code,
                new_values=_model_values(obj),
                request=request,
            )
            messages.success(request, "Item added successfully.")
            return redirect("item_list")
    else:
        form = ItemForm()
    return render(
        request,
        "inventory/item_form.html",
        {"form": form, "title": "Add Item"},
    )


@permission_required("inventory.change_item", raise_exception=True)
def item_update(request, pk):
    item = get_object_or_404(Item, pk=pk)
    old = _model_values(item)
    if request.method == "POST":
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            obj = form.save()
            log_activity(
                request.user,
                "Update Item",
                app_label="inventory",
                model_name="Item",
                object_id=obj.pk,
                object_repr=obj.item_code,
                old_values=old,
                new_values=_model_values(obj),
                request=request,
            )
            messages.success(request, "Item updated successfully.")
            return redirect("item_list")
    else:
        form = ItemForm(instance=item)
    return render(
        request,
        "inventory/item_form.html",
        {"form": form, "title": f"Edit Item: {item.name}"},
    )


@permission_required("inventory.delete_item", raise_exception=True)
def item_delete(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == "POST":
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
        messages.success(request, "Item deleted successfully.")
        return redirect("item_list")
    return render(
        request,
        "inventory/item_confirm_delete.html",
        {"item": item},
    )


# ---------------- Warehouses ----------------

@permission_required("inventory.view_warehouse", raise_exception=True)
def warehouse_list(request):
    query = request.GET.get("q", "")
    warehouses = Warehouse.objects.all().order_by("code")
    if query:
        warehouses = warehouses.filter(
            Q(code__icontains=query)
            | Q(name__icontains=query)
            | Q(location__icontains=query)
        )
    paginator = Paginator(warehouses, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "inventory/warehouse_list.html",
        {"page_obj": page_obj, "query": query},
    )


@permission_required("inventory.add_warehouse", raise_exception=True)
def warehouse_create(request):
    if request.method == "POST":
        form = WarehouseForm(request.POST)
        if form.is_valid():
            obj = form.save()
            log_activity(
                request.user,
                "Create Warehouse",
                app_label="inventory",
                model_name="Warehouse",
                object_id=obj.pk,
                object_repr=obj.code,
                new_values=_model_values(obj),
                request=request,
            )
            messages.success(request, "Warehouse added successfully.")
            return redirect("warehouse_list")
    else:
        form = WarehouseForm()
    return render(
        request,
        "inventory/warehouse_form.html",
        {"form": form, "title": "Add Warehouse"},
    )


@permission_required("inventory.change_warehouse", raise_exception=True)
def warehouse_update(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    old = _model_values(warehouse)
    if request.method == "POST":
        form = WarehouseForm(request.POST, instance=warehouse)
        if form.is_valid():
            obj = form.save()
            log_activity(
                request.user,
                "Update Warehouse",
                app_label="inventory",
                model_name="Warehouse",
                object_id=obj.pk,
                object_repr=obj.code,
                old_values=old,
                new_values=_model_values(obj),
                request=request,
            )
            messages.success(request, "Warehouse updated successfully.")
            return redirect("warehouse_list")
    else:
        form = WarehouseForm(instance=warehouse)
    return render(
        request,
        "inventory/warehouse_form.html",
        {"form": form, "title": f"Edit Warehouse: {warehouse.name}"},
    )


@permission_required("inventory.delete_warehouse", raise_exception=True)
def warehouse_delete(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    if request.method == "POST":
        log_activity(
            request.user,
            "Delete Warehouse",
            app_label="inventory",
            model_name="Warehouse",
            object_id=warehouse.pk,
            object_repr=warehouse.code,
            request=request,
        )
        warehouse.delete()
        messages.success(request, "Warehouse deleted successfully.")
        return redirect("warehouse_list")
    return render(
        request,
        "inventory/warehouse_confirm_delete.html",
        {"warehouse": warehouse},
    )


# ---------------- Stock ----------------

@permission_required("inventory.view_stock", raise_exception=True)
def stock_list(request):
    query = request.GET.get("q", "")
    stocks = Stock.objects.select_related("item", "warehouse").order_by(
        "item__item_code", "warehouse__name"
    )
    if query:
        stocks = stocks.filter(
            Q(item__name__icontains=query)
            | Q(item__item_code__icontains=query)
            | Q(warehouse__name__icontains=query)
        )
    paginator = Paginator(stocks, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "inventory/stock_list.html",
        {"page_obj": page_obj, "query": query},
    )


@permission_required("inventory.can_manage_stock", raise_exception=True)
def stock_in(request):
    """Receive stock into a warehouse."""
    if request.method == "POST":
        form = StockInForm(request.POST)
        if form.is_valid():
            item = form.cleaned_data["item"]
            warehouse = form.cleaned_data["warehouse"]
            qty = form.cleaned_data["quantity"]

            with transaction.atomic():
                stock, created = Stock.objects.get_or_create(
                    item=item,
                    warehouse=warehouse,
                    defaults={"quantity": qty},
                )
                if not created:
                    stock.quantity += qty
                    stock.save()

                balance_after = stock.quantity
                _record_stock_movement(
                    item, warehouse, qty, "Stock In", request.user,
                    balance_after,
                )

            log_activity(
                request.user,
                "Stock In",
                app_label="inventory",
                model_name="Stock",
                object_id=f"{item.item_code}@{warehouse.code}",
                object_repr=f"{item.name} +{qty} @ {warehouse.name}",
                new_values={"item": item.item_code, "warehouse": warehouse.code, "quantity": qty},
                request=request,
            )
            messages.success(
                request,
                f"Stock In completed: {item.name} +{qty} at {warehouse.name}.",
            )
            return redirect("stock_list")
    else:
        form = StockInForm()
    return render(
        request,
        "inventory/stock_form.html",
        {"form": form, "title": "Stock In"},
    )


@permission_required("inventory.can_manage_stock", raise_exception=True)
def stock_out(request):
    """Issue stock from a warehouse."""
    if request.method == "POST":
        form = StockOutForm(request.POST)
        if form.is_valid():
            item = form.cleaned_data["item"]
            warehouse = form.cleaned_data["warehouse"]
            qty = form.cleaned_data["quantity"]
            stock = Stock.objects.filter(item=item, warehouse=warehouse).first()
            if not stock or stock.quantity < qty:
                messages.error(request, "Insufficient stock.")
            else:
                with transaction.atomic():
                    stock.quantity -= qty
                    stock.save()
                    _record_stock_movement(
                        item, warehouse, -qty, "Stock Out", request.user,
                        stock.quantity,
                    )

                log_activity(
                    request.user,
                    "Stock Out",
                    app_label="inventory",
                    model_name="Stock",
                    object_id=f"{item.item_code}@{warehouse.code}",
                    object_repr=f"{item.name} -{qty} @ {warehouse.name}",
                    new_values={"item": item.item_code, "warehouse": warehouse.code, "quantity": -qty},
                    request=request,
                )
                messages.success(
                    request,
                    f"Stock Out completed: {item.name} -{qty} from {warehouse.name}.",
                )
                return redirect("stock_list")
    else:
        form = StockOutForm()
    return render(
        request,
        "inventory/stock_form.html",
        {"form": form, "title": "Stock Out"},
    )


# ---------------- Stock Transfers ----------------

@permission_required("inventory.view_stocktransfer", raise_exception=True)
def stocktransfer_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    transfers = StockTransfer.objects.select_related(
        "item", "from_warehouse", "to_warehouse"
    ).order_by("-created_at")

    if query:
        transfers = transfers.filter(
            Q(transfer_number__icontains=query) | Q(item__name__icontains=query)
        )
    if status:
        transfers = transfers.filter(status=status)

    statuses = ["Draft", "Pending", "Approved", "In Transit", "Completed", "Cancelled", "Rejected"]
    paginator = Paginator(transfers, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "inventory/stocktransfer_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "status": status,
            "statuses": statuses,
        },
    )


@permission_required("inventory.add_stocktransfer", raise_exception=True)
def stocktransfer_create(request):
    if request.method == "POST":
        form = StockTransferForm(request.POST)
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
                new_values={
                    "transfer_number": transfer.transfer_number,
                    "item": str(transfer.item),
                    "from": str(transfer.from_warehouse),
                    "to": str(transfer.to_warehouse),
                    "quantity": transfer.quantity,
                },
                request=request,
            )
            messages.success(
                request,
                f"Stock transfer {transfer.transfer_number} created as Pending.",
            )
            return redirect("stocktransfer_detail", pk=transfer.pk)
    else:
        form = StockTransferForm()
    return render(
        request,
        "inventory/stocktransfer_form.html",
        {"form": form, "title": "Create Stock Transfer"},
    )


@permission_required("inventory.view_stocktransfer", raise_exception=True)
def stocktransfer_detail(request, pk):
    transfer = get_object_or_404(
        StockTransfer.objects.select_related(
            "item", "from_warehouse", "to_warehouse", "requested_by", "approved_by"
        ),
        pk=pk,
    )
    return render(
        request,
        "inventory/stocktransfer_detail.html",
        {"transfer": transfer},
    )


@permission_required("inventory.change_stocktransfer", raise_exception=True)
def stocktransfer_complete(request, pk):
    """Complete a pending transfer and move stock."""
    transfer = get_object_or_404(StockTransfer, pk=pk)
    if transfer.status != "Pending":
        messages.error(request, "Only pending transfers can be completed.")
        return redirect("stocktransfer_detail", pk=pk)

    source_stock = Stock.objects.filter(
        item=transfer.item, warehouse=transfer.from_warehouse
    ).first()
    if not source_stock or source_stock.quantity < transfer.quantity:
        messages.error(request, "Insufficient stock in source warehouse.")
        return redirect("stocktransfer_detail", pk=pk)

    with transaction.atomic():
        source_stock.quantity -= transfer.quantity
        source_stock.save()
        _record_stock_movement(
            transfer.item, transfer.from_warehouse, -transfer.quantity,
            "Transfer Out", request.user, source_stock.quantity,
            reference_document="StockTransfer", reference_number=transfer.transfer_number,
        )

        dest_stock, _ = Stock.objects.get_or_create(
            item=transfer.item,
            warehouse=transfer.to_warehouse,
            defaults={"quantity": 0},
        )
        dest_stock.quantity += transfer.quantity
        dest_stock.save()
        _record_stock_movement(
            transfer.item, transfer.to_warehouse, transfer.quantity,
            "Transfer In", request.user, dest_stock.quantity,
            reference_document="StockTransfer", reference_number=transfer.transfer_number,
        )

        transfer.status = "Completed"
        transfer.approved_by = request.user
        transfer.save()

    log_activity(
        request.user,
        "Complete Stock Transfer",
        app_label="inventory",
        model_name="StockTransfer",
        object_id=transfer.pk,
        object_repr=transfer.transfer_number,
        new_values={"status": "Completed"},
        request=request,
    )
    messages.success(request, "Transfer completed.")
    return redirect("stocktransfer_detail", pk=pk)


@permission_required("inventory.change_stocktransfer", raise_exception=True)
def stocktransfer_cancel(request, pk):
    """Cancel a pending transfer."""
    transfer = get_object_or_404(StockTransfer, pk=pk)
    if transfer.status != "Pending":
        messages.error(request, "Only pending transfers can be cancelled.")
        return redirect("stocktransfer_detail", pk=pk)
    transfer.status = "Cancelled"
    transfer.save()
    log_activity(
        request.user,
        "Cancel Stock Transfer",
        app_label="inventory",
        model_name="StockTransfer",
        object_id=transfer.pk,
        object_repr=transfer.transfer_number,
        new_values={"status": "Cancelled"},
        request=request,
    )
    messages.success(request, "Transfer cancelled.")
    return redirect("stocktransfer_detail", pk=pk)