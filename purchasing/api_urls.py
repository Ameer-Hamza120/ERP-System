from django.urls import path
from . import views_api

urlpatterns = [
    path("suppliers/", views_api.api_suppliers, name="api_suppliers"),
    path("suppliers/<int:pk>/", views_api.api_supplier_detail, name="api_supplier_detail"),
    path("purchase-requests/", views_api.api_purchase_requests, name="api_purchase_requests"),
    path("purchase-quotations/", views_api.api_purchase_quotations, name="api_purchase_quotations"),
    path("purchase-orders/", views_api.api_purchase_orders, name="api_purchase_orders"),
    path("goods-receipts/", views_api.api_goods_receipts, name="api_goods_receipts"),
    path("ap-invoices/", views_api.api_ap_invoices, name="api_ap_invoices"),
    path("ap-credit-memos/", views_api.api_ap_credit_memos, name="api_ap_credit_memos"),
    path("outgoing-payments/", views_api.api_outgoing_payments, name="api_outgoing_payments"),
]