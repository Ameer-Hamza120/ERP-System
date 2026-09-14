import csv
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.http import HttpResponse
from django.shortcuts import render

from inventory.models import Item, Stock, StockTransfer


@permission_required("inventory.view_stock", raise_exception=True)
def inventory_report(request):
    """Inventory report: item, group, warehouse, quantity."""
    query = request.GET.get("q", "")
    stocks = Stock.objects.select_related("item__group", "warehouse").order_by(
        "item__item_code"
    )
    if query:
        stocks = stocks.filter(
            Q(item__item_code__icontains=query)
            | Q(item__name__icontains=query)
            | Q(warehouse__name__icontains=query)
        )
    paginator = Paginator(stocks, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "reports/inventory_report.html",
        {"page_obj": page_obj, "query": query},
    )


@permission_required("inventory.view_item", raise_exception=True)
def low_stock_report(request):
    """Items whose total stock is below or equal to the minimum stock level."""
    query = request.GET.get("q", "")
    items = Item.objects.annotate(
        total_stock=Sum("stock_records__quantity")
    ).filter(total_stock__lte=F("minimum_stock_level"))
    if query:
        items = items.filter(
            Q(item_code__icontains=query) | Q(name__icontains=query)
        )
    items = items.order_by("item_code")
    return render(
        request,
        "reports/low_stock_report.html",
        {"items": items, "query": query},
    )


@permission_required("inventory.view_stocktransfer", raise_exception=True)
def stock_transfer_report(request):
    """All stock transfers with filters."""
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
    statuses = ["Pending", "Completed", "Cancelled"]
    paginator = Paginator(transfers, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "reports/stock_transfer_report.html",
        {
            "page_obj": page_obj,
            "query": query,
            "status": status,
            "statuses": statuses,
        },
    )


@permission_required("inventory.view_stock", raise_exception=True)
def export_inventory_csv(request):
    """Export inventory report as CSV."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="inventory_report.csv"'
    writer = csv.writer(response)
    writer.writerow(["Item Code", "Item Name", "Item Group", "Warehouse", "Quantity"])
    stocks = Stock.objects.select_related("item__group", "warehouse").order_by(
        "item__item_code"
    )
    for stock in stocks:
        writer.writerow(
            [
                stock.item.item_code,
                stock.item.name,
                stock.item.group.name if stock.item.group else "",
                stock.warehouse.name,
                stock.quantity,
            ]
        )
    return response


@permission_required("inventory.view_item", raise_exception=True)
def export_low_stock_csv(request):
    """Export low stock report as CSV."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="low_stock_report.csv"'
    writer = csv.writer(response)
    writer.writerow(["Item Code", "Item Name", "Minimum Stock", "Current Stock"])
    items = (
        Item.objects.annotate(total_stock=Sum("stock_records__quantity"))
        .filter(total_stock__lte=F("minimum_stock_level"))
        .order_by("item_code")
    )
    for item in items:
        writer.writerow(
            [item.item_code, item.name, item.minimum_stock_level, item.total_stock]
        )
    return response


@permission_required("inventory.view_stocktransfer", raise_exception=True)
def export_transfer_csv(request):
    """Export stock transfer report as CSV."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="stock_transfer_report.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "Transfer Number",
            "Item",
            "From Warehouse",
            "To Warehouse",
            "Quantity",
            "Date",
            "Status",
        ]
    )
    transfers = StockTransfer.objects.select_related(
        "item", "from_warehouse", "to_warehouse"
    ).order_by("-created_at")
    for transfer in transfers:
        writer.writerow(
            [
                transfer.transfer_number,
                transfer.item.name,
                transfer.from_warehouse.name,
                transfer.to_warehouse.name,
                transfer.quantity,
                transfer.transfer_date,
                transfer.status,
            ]
        )
    return response
