from django.urls import path
from . import views

urlpatterns = [
    # Customers
    path("customers/", views.customer_list, name="customer_list"),
    path("customers/add/", views.customer_create, name="customer_create"),
    path("customers/<int:pk>/edit/", views.customer_update, name="customer_update"),
    path("customers/<int:pk>/delete/", views.customer_delete, name="customer_delete"),
    # Sales Quotations
    path("quotations/", views.salesquotation_list, name="salesquotation_list"),
    path("quotations/add/", views.salesquotation_create, name="salesquotation_create"),
    path("quotations/<int:pk>/", views.salesquotation_detail, name="salesquotation_detail"),
    path("quotations/<int:pk>/edit/", views.salesquotation_update, name="salesquotation_update"),
    path("quotations/<int:pk>/accept/", views.salesquotation_accept, name="salesquotation_accept"),
    path("quotations/<int:pk>/cancel/", views.salesquotation_cancel, name="salesquotation_cancel"),
    # Sales Orders
    path("orders/", views.salesorder_list, name="salesorder_list"),
    path("orders/add/", views.salesorder_create, name="salesorder_create"),
    path("orders/<int:pk>/", views.salesorder_detail, name="salesorder_detail"),
    path("orders/<int:pk>/edit/", views.salesorder_update, name="salesorder_update"),
    path("orders/<int:pk>/complete/", views.salesorder_complete, name="salesorder_complete"),
    path("orders/<int:pk>/cancel/", views.salesorder_cancel, name="salesorder_cancel"),
    # Deliveries
    path("deliveries/", views.delivery_list, name="delivery_list"),
    path("deliveries/add/", views.delivery_create, name="delivery_create"),
    path("deliveries/<int:pk>/", views.delivery_detail, name="delivery_detail"),
    path("deliveries/<int:pk>/edit/", views.delivery_update, name="delivery_update"),
    path("deliveries/<int:pk>/post/", views.delivery_post, name="delivery_post"),
    path("deliveries/<int:pk>/cancel/", views.delivery_cancel, name="delivery_cancel"),
    # Return Requests
    path("return-requests/", views.returnrequest_list, name="returnrequest_list"),
    path("return-requests/add/", views.returnrequest_create, name="returnrequest_create"),
    path("return-requests/<int:pk>/", views.returnrequest_detail, name="returnrequest_detail"),
    path("return-requests/<int:pk>/approve/", views.returnrequest_approve, name="returnrequest_approve"),
    path("return-requests/<int:pk>/reject/", views.returnrequest_reject, name="returnrequest_reject"),
    # Returns
    path("returns/", views.salesreturn_list, name="salesreturn_list"),
    path("returns/add/", views.salesreturn_create, name="salesreturn_create"),
    path("returns/<int:pk>/", views.salesreturn_detail, name="salesreturn_detail"),
    path("returns/<int:pk>/post/", views.salesreturn_post, name="salesreturn_post"),
    path("returns/<int:pk>/cancel/", views.salesreturn_cancel, name="salesreturn_cancel"),
    # A/R Invoices
    path("invoices/", views.arinvoice_list, name="arinvoice_list"),
    path("invoices/add/", views.arinvoice_create, name="arinvoice_create"),
    path("invoices/<int:pk>/", views.arinvoice_detail, name="arinvoice_detail"),
    path("invoices/<int:pk>/cancel/", views.arinvoice_cancel, name="arinvoice_cancel"),
    # A/R Credit Memos
    path("credit-memos/", views.arcreditmemo_list, name="arcreditmemo_list"),
    path("credit-memos/add/", views.arcreditmemo_create, name="arcreditmemo_create"),
    path("credit-memos/<int:pk>/", views.arcreditmemo_detail, name="arcreditmemo_detail"),
    path("credit-memos/<int:pk>/apply/", views.arcreditmemo_apply, name="arcreditmemo_apply"),
    path("credit-memos/<int:pk>/cancel/", views.arcreditmemo_cancel, name="arcreditmemo_cancel"),
    # Incoming Payments
    path("payments/", views.incomingpayment_list, name="incomingpayment_list"),
    path("payments/add/", views.incomingpayment_create, name="incomingpayment_create"),
    path("payments/<int:pk>/", views.incomingpayment_detail, name="incomingpayment_detail"),
    path("payments/<int:pk>/complete/", views.incomingpayment_complete, name="incomingpayment_complete"),
    path("payments/<int:pk>/cancel/", views.incomingpayment_cancel, name="incomingpayment_cancel"),
]