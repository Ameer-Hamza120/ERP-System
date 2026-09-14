from django.urls import path
from . import views_api

urlpatterns = [
    path("customers/", views_api.api_customers, name="api_customers"),
    path("customers/<int:pk>/", views_api.api_customer_detail, name="api_customer_detail"),
    path("sales-quotations/", views_api.api_sales_quotations, name="api_sales_quotations"),
    path("sales-orders/", views_api.api_sales_orders, name="api_sales_orders"),
    path("deliveries/", views_api.api_deliveries, name="api_deliveries"),
    path("return-requests/", views_api.api_return_requests, name="api_return_requests"),
    path("sales-returns/", views_api.api_sales_returns, name="api_sales_returns"),
    path("ar-invoices/", views_api.api_ar_invoices, name="api_ar_invoices"),
    path("ar-credit-memos/", views_api.api_ar_credit_memos, name="api_ar_credit_memos"),
    path("incoming-payments/", views_api.api_incoming_payments, name="api_incoming_payments"),
]