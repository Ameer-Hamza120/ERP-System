from django.urls import path
from . import views

urlpatterns = [
    # Item Groups
    path("item-groups/", views.itemgroup_list, name="itemgroup_list"),
    path("item-groups/add/", views.itemgroup_create, name="itemgroup_create"),
    path(
        "item-groups/<int:pk>/edit/",
        views.itemgroup_update,
        name="itemgroup_update",
    ),
    path(
        "item-groups/<int:pk>/delete/",
        views.itemgroup_delete,
        name="itemgroup_delete",
    ),
    # Items
    path("items/", views.item_list, name="item_list"),
    path("items/add/", views.item_create, name="item_create"),
    path("items/<int:pk>/", views.item_detail, name="item_detail"),
    path("items/<int:pk>/edit/", views.item_update, name="item_update"),
    path("items/<int:pk>/delete/", views.item_delete, name="item_delete"),
    # Warehouses
    path("warehouses/", views.warehouse_list, name="warehouse_list"),
    path("warehouses/add/", views.warehouse_create, name="warehouse_create"),
    path(
        "warehouses/<int:pk>/edit/",
        views.warehouse_update,
        name="warehouse_update",
    ),
    path(
        "warehouses/<int:pk>/delete/",
        views.warehouse_delete,
        name="warehouse_delete",
    ),
    # Stock
    path("stock/", views.stock_list, name="stock_list"),
    path("stock/in/", views.stock_in, name="stock_in"),
    path("stock/out/", views.stock_out, name="stock_out"),
    # Stock Transfers
    path("transfers/", views.stocktransfer_list, name="stocktransfer_list"),
    path("transfers/add/", views.stocktransfer_create, name="stocktransfer_create"),
    path(
        "transfers/<int:pk>/",
        views.stocktransfer_detail,
        name="stocktransfer_detail",
    ),
    path(
        "transfers/<int:pk>/complete/",
        views.stocktransfer_complete,
        name="stocktransfer_complete",
    ),
    path(
        "transfers/<int:pk>/cancel/",
        views.stocktransfer_cancel,
        name="stocktransfer_cancel",
    ),
]