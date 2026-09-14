from django.urls import path
from . import views

urlpatterns = [
    # Suppliers
    path("suppliers/", views.supplier_list, name="supplier_list"),
    path("suppliers/add/", views.supplier_create, name="supplier_create"),
    path("suppliers/<int:pk>/edit/", views.supplier_update, name="supplier_update"),
    path("suppliers/<int:pk>/delete/", views.supplier_delete, name="supplier_delete"),
    # Purchase Requests
    path("requests/", views.purchaserequest_list, name="purchaserequest_list"),
    path("requests/add/", views.purchaserequest_create, name="purchaserequest_create"),
    path("requests/<int:pk>/", views.purchaserequest_detail, name="purchaserequest_detail"),
    path("requests/<int:pk>/approve/", views.purchaserequest_approve, name="purchaserequest_approve"),
    path("requests/<int:pk>/reject/", views.purchaserequest_reject, name="purchaserequest_reject"),
    # Purchase Quotations
    path("quotations/", views.purchasequotation_list, name="purchasequotation_list"),
    path("quotations/add/", views.purchasequotation_create, name="purchasequotation_create"),
    path("quotations/<int:pk>/", views.purchasequotation_detail, name="purchasequotation_detail"),
    path("quotations/<int:pk>/accept/", views.purchasequotation_accept, name="purchasequotation_accept"),
    path("quotations/<int:pk>/reject/", views.purchasequotation_reject, name="purchasequotation_reject"),
    # Purchase Orders
    path("orders/", views.purchaseorder_list, name="purchaseorder_list"),
    path("orders/add/", views.purchaseorder_create, name="purchaseorder_create"),
    path("orders/<int:pk>/", views.purchaseorder_detail, name="purchaseorder_detail"),
    path("orders/<int:pk>/complete/", views.purchaseorder_complete, name="purchaseorder_complete"),
    path("orders/<int:pk>/cancel/", views.purchaseorder_cancel, name="purchaseorder_cancel"),
    # Goods Receipts
    path("goods-receipts/", views.goodsreceipt_list, name="goodsreceipt_list"),
    path("goods-receipts/add/", views.goodsreceipt_create, name="goodsreceipt_create"),
    path("goods-receipts/<int:pk>/", views.goodsreceipt_detail, name="goodsreceipt_detail"),
    path("goods-receipts/<int:pk>/post/", views.goodsreceipt_post, name="goodsreceipt_post"),
    path("goods-receipts/<int:pk>/cancel/", views.goodsreceipt_cancel, name="goodsreceipt_cancel"),
    # A/P Invoices
    path("invoices/", views.apinvoice_list, name="apinvoice_list"),
    path("invoices/add/", views.apinvoice_create, name="apinvoice_create"),
    path("invoices/<int:pk>/", views.apinvoice_detail, name="apinvoice_detail"),
    path("invoices/<int:pk>/cancel/", views.apinvoice_cancel, name="apinvoice_cancel"),
    # A/P Credit Memos
    path("credit-memos/", views.apcreditmemo_list, name="apcreditmemo_list"),
    path("credit-memos/add/", views.apcreditmemo_create, name="apcreditmemo_create"),
    path("credit-memos/<int:pk>/", views.apcreditmemo_detail, name="apcreditmemo_detail"),
    path("credit-memos/<int:pk>/apply/", views.apcreditmemo_apply, name="apcreditmemo_apply"),
    path("credit-memos/<int:pk>/cancel/", views.apcreditmemo_cancel, name="apcreditmemo_cancel"),
    # Outgoing Payments
    path("payments/", views.outgoingpayment_list, name="outgoingpayment_list"),
    path("payments/add/", views.outgoingpayment_create, name="outgoingpayment_create"),
    path("payments/<int:pk>/", views.outgoingpayment_detail, name="outgoingpayment_detail"),
    path("payments/<int:pk>/complete/", views.outgoingpayment_complete, name="outgoingpayment_complete"),
    path("payments/<int:pk>/cancel/", views.outgoingpayment_cancel, name="outgoingpayment_cancel"),
]