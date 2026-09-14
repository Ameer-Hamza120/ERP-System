from django.urls import path
from . import views_api

urlpatterns = [
    path("items/", views_api.api_items, name="api_items"),
    path("items/<int:pk>/", views_api.api_item_detail, name="api_item_detail"),
    path("warehouses/", views_api.api_warehouses, name="api_warehouses"),
    path("stock/", views_api.api_stock, name="api_stock"),
    path("stock-movements/", views_api.api_stock_movements, name="api_stock_movements"),
    path("transfers/", views_api.api_transfers, name="api_transfers"),
]