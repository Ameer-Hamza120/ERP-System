from django.urls import path
from . import views

urlpatterns = [
    path("inventory/", views.inventory_report, name="inventory_report"),
    path("low-stock/", views.low_stock_report, name="low_stock_report"),
    path(
        "stock-transfers/",
        views.stock_transfer_report,
        name="stock_transfer_report",
    ),
    path("inventory/csv/", views.export_inventory_csv, name="export_inventory_csv"),
    path("low-stock/csv/", views.export_low_stock_csv, name="export_low_stock_csv"),
    path(
        "stock-transfers/csv/",
        views.export_transfer_csv,
        name="export_transfer_csv",
    ),
]
