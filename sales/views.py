from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from audit.log import log_activity
from inventory.models import Stock

from .forms import (
    ARCreditMemoForm,
    ARCreditMemoLineFormSet,
    ARInvoiceForm,
    ARInvoiceLineFormSet,
    CustomerForm,
    DeliveryForm,
    DeliveryLineFormSet,
    IncomingPaymentForm,
    ReturnRequestForm,
    ReturnRequestLineFormSet,
    SalesOrderForm,
    SalesOrderLineFormSet,
    SalesQuotationForm,
    SalesQuotationLineFormSet,
    SalesReturnForm,
    SalesReturnLineFormSet,
)
from .models import (
    ARCreditMemo,
    ARInvoice,
    Customer,
    Delivery,
    IncomingPayment,
    ReturnRequest,
    SalesOrder,
    SalesQuotation,
    SalesReturn,
)
from common.utils import (
    model_values as _model_values,
    get_or_none as _get_or_none,
    list_context as _list_context,
    action_url as _action_url,
)
from inventory.services import record_stock_movement as _record_stock_movement


# ===================================================================
# Customers
# ===================================================================

@permission_required("sales.view_customer", raise_exception=True)
def customer_list(request):
    query = request.GET.get("q", "")
    customers = Customer.objects.all().order_by("name")
    if query:
        customers = customers.filter(
            Q(name__icontains=query)
            | Q(customer_code__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query)
        )
    paginator = Paginator(customers, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "sales/customer_list.html",
        {"page_obj": page_obj, "query": query},
    )


@permission_required("sales.add_customer", raise_exception=True)
def customer_create(request):
    if request.method == "POST":
        form = CustomerForm(request.POST)
        if form.is_valid():
            obj = form.save()
            log_activity(
                request.user, "Create Customer", app_label="sales",
                model_name="Customer", object_id=obj.pk, object_repr=obj.name,
                new_values=_model_values(obj), request=request,
            )
            messages.success(request, "Customer added successfully.")
            return redirect("customer_list")
    else:
        form = CustomerForm()
    return render(request, "sales/customer_form.html", {"form": form, "title": "Add Customer"})


@permission_required("sales.change_customer", raise_exception=True)
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    old = _model_values(customer)
    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            obj = form.save()
            log_activity(
                request.user, "Update Customer", app_label="sales",
                model_name="Customer", object_id=obj.pk, object_repr=obj.name,
                old_values=old, new_values=_model_values(obj), request=request,
            )
            messages.success(request, "Customer updated successfully.")
            return redirect("customer_list")
    else:
        form = CustomerForm(instance=customer)
    return render(
        request, "sales/customer_form.html",
        {"form": form, "title": f"Edit Customer: {customer.name}"},
    )


@permission_required("sales.delete_customer", raise_exception=True)
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.method == "POST":
        log_activity(
            request.user, "Delete Customer", app_label="sales",
            model_name="Customer", object_id=customer.pk, object_repr=customer.name,
            request=request,
        )
        customer.delete()
        messages.success(request, "Customer deleted successfully.")
        return redirect("customer_list")
    return render(request, "sales/customer_confirm_delete.html", {"customer": customer})


# ===================================================================
# Sales Quotation (A)
# ===================================================================

@permission_required("sales.view_salesquotation", raise_exception=True)
def salesquotation_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    quotes = SalesQuotation.objects.select_related("customer").order_by("-created_at")
    if query:
        quotes = quotes.filter(
            Q(quotation_number__icontains=query) | Q(customer__name__icontains=query)
        )
    if status:
        quotes = quotes.filter(status=status)
    paginator = Paginator(quotes, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = _list_context(
        "Sales Quotations",
        [
            {"label": "Quotation #", "key": "quotation_number", "link": "salesquotation_detail"},
            {"label": "Customer", "key": "customer"},
            {"label": "Date", "key": "quotation_date"},
            {"label": "Valid Until", "key": "valid_until"},
            {"label": "Status", "key": "status"},
        ],
        "salesquotation_create",
        "salesquotation_detail",
        ["Draft", "Open", "Accepted", "Expired", "Cancelled"],
    )
    context.update({"page_obj": page_obj, "query": query, "status": status})
    return render(request, "sales/doc_list.html", context)


@permission_required("sales.add_salesquotation", raise_exception=True)
def salesquotation_create(request):
    if request.method == "POST":
        form = SalesQuotationForm(request.POST)
        formset = SalesQuotationLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            quote = form.save(commit=False)
            quote.created_by = request.user
            quote.status = "Open"
            quote.save()
            formset.instance = quote
            formset.save()
            log_activity(
                request.user, "Create Sales Quotation", app_label="sales",
                model_name="SalesQuotation", object_id=quote.pk, object_repr=quote.quotation_number,
                new_values={"quotation_number": quote.quotation_number, "customer": str(quote.customer)},
                request=request,
            )
            messages.success(request, f"Sales quotation {quote.quotation_number} created.")
            return redirect("salesquotation_detail", pk=quote.pk)
    else:
        form = SalesQuotationForm()
        formset = SalesQuotationLineFormSet()
    return render(
        request, "sales/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Create Sales Quotation",
            "lines_title": "Quotation Lines",
            "cancel_url": "salesquotation_list",
        },
    )


@permission_required("sales.view_salesquotation", raise_exception=True)
def salesquotation_detail(request, pk):
    quote = get_object_or_404(SalesQuotation.objects.select_related("customer"), pk=pk)
    actions = []
    if quote.status in ("Draft", "Open"):
        actions.append(("Accept Quotation", _action_url("salesquotation_accept", pk=quote.pk), ""))
        actions.append(("Create Sales Order", _action_url("salesorder_create", query={"quotation": quote.pk}), ""))
    if quote.status in ("Draft", "Open"):
        actions.append(("Cancel Quotation", _action_url("salesquotation_cancel", pk=quote.pk), "btn-danger"))
    return render(
        request, "sales/doc_detail.html",
        {
            "doc": quote,
            "doc_number": quote.quotation_number,
            "info_fields": [
                ("Customer", quote.customer.name),
                ("Date", quote.quotation_date),
                ("Valid Until", quote.valid_until or "-"),
                ("Status", quote.get_status_display()),
                ("Remarks", quote.remarks or "-"),
            ],
            "lines": quote.lines.select_related("item"),
            "lines_title": "Quotation Lines",
            "total": quote.total,
            "actions": actions,
            "list_url": "salesquotation_list",
        },
    )


@permission_required("sales.change_salesquotation", raise_exception=True)
def salesquotation_update(request, pk):
    quote = get_object_or_404(SalesQuotation, pk=pk)
    if quote.status not in ("Draft", "Open"):
        messages.error(request, "Only Draft or Open quotations can be edited.")
        return redirect("salesquotation_detail", pk=pk)
    old = _model_values(quote)
    if request.method == "POST":
        form = SalesQuotationForm(request.POST, instance=quote)
        formset = SalesQuotationLineFormSet(request.POST, instance=quote)
        if form.is_valid() and formset.is_valid():
            obj = form.save()
            formset.save()
            log_activity(
                request.user, "Update Sales Quotation", app_label="sales",
                model_name="SalesQuotation", object_id=obj.pk, object_repr=obj.quotation_number,
                old_values=old, new_values=_model_values(obj), request=request,
            )
            messages.success(request, "Quotation updated successfully.")
            return redirect("salesquotation_detail", pk=pk)
    else:
        form = SalesQuotationForm(instance=quote)
        formset = SalesQuotationLineFormSet(instance=quote)
    return render(
        request, "sales/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": f"Edit Quotation: {quote.quotation_number}",
            "lines_title": "Quotation Lines",
            "cancel_url": "salesquotation_detail",
        },
    )


@permission_required("sales.change_salesquotation", raise_exception=True)
def salesquotation_accept(request, pk):
    quote = get_object_or_404(SalesQuotation, pk=pk)
    if quote.status != "Open":
        messages.error(request, "Only Open quotations can be accepted.")
        return redirect("salesquotation_detail", pk=pk)
    quote.status = "Accepted"
    quote.save()
    log_activity(
        request.user, "Accept Sales Quotation", app_label="sales",
        model_name="SalesQuotation", object_id=quote.pk, object_repr=quote.quotation_number,
        new_values={"status": "Accepted"}, request=request,
    )
    messages.success(request, "Quotation accepted. You can now create a Sales Order.")
    return redirect("salesquotation_detail", pk=pk)


@permission_required("sales.change_salesquotation", raise_exception=True)
def salesquotation_cancel(request, pk):
    quote = get_object_or_404(SalesQuotation, pk=pk)
    if quote.status not in ("Draft", "Open"):
        messages.error(request, "Only Draft or Open quotations can be cancelled.")
        return redirect("salesquotation_detail", pk=pk)
    quote.status = "Cancelled"
    quote.save()
    log_activity(
        request.user, "Cancel Sales Quotation", app_label="sales",
        model_name="SalesQuotation", object_id=quote.pk, object_repr=quote.quotation_number,
        new_values={"status": "Cancelled"}, request=request,
    )
    messages.success(request, "Quotation cancelled.")
    return redirect("salesquotation_detail", pk=pk)


# ===================================================================
# Sales Order (B)
# ===================================================================

@permission_required("sales.view_salesorder", raise_exception=True)
def salesorder_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    orders = SalesOrder.objects.select_related("customer", "quotation").order_by("-created_at")
    if query:
        orders = orders.filter(
            Q(order_number__icontains=query) | Q(customer__name__icontains=query)
        )
    if status:
        orders = orders.filter(status=status)
    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = _list_context(
        "Sales Orders",
        [
            {"label": "Order #", "key": "order_number", "link": "salesorder_detail"},
            {"label": "Customer", "key": "customer"},
            {"label": "Date", "key": "order_date"},
            {"label": "Quotation", "key": "quotation"},
            {"label": "Status", "key": "status"},
        ],
        "salesorder_create",
        "salesorder_detail",
        ["Draft", "Open", "Completed", "Cancelled"],
    )
    context.update({"page_obj": page_obj, "query": query, "status": status})
    return render(request, "sales/doc_list.html", context)


@permission_required("sales.add_salesorder", raise_exception=True)
def salesorder_create(request):
    """Create a Sales Order, optionally from an accepted quotation (?quotation=<id>)."""
    quotation = _get_or_none(SalesQuotation, request.GET.get("quotation"))
    initial = {}
    line_initial = []
    if quotation:
        initial = {
            "customer": quotation.customer,
            "quotation": quotation,
        }
        line_initial = [
            {
                "item": l.item_id,
                "quantity": l.quantity,
                "unit_price": l.unit_price,
                "discount_percent": l.discount_percent,
                "tax_percent": l.tax_percent,
            }
            for l in quotation.lines.all()
        ]

    if request.method == "POST":
        form = SalesOrderForm(request.POST)
        formset = SalesOrderLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            order = form.save(commit=False)
            order.created_by = request.user
            order.status = "Open"
            order.save()
            formset.instance = order
            formset.save()
            log_activity(
                request.user, "Create Sales Order", app_label="sales",
                model_name="SalesOrder", object_id=order.pk, object_repr=order.order_number,
                new_values={"order_number": order.order_number, "customer": str(order.customer)},
                request=request,
            )
            messages.success(request, f"Sales order {order.order_number} created.")
            return redirect("salesorder_detail", pk=order.pk)
    else:
        form = SalesOrderForm(initial=initial)
        formset = SalesOrderLineFormSet(initial=line_initial)
    return render(
        request, "sales/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Create Sales Order",
            "lines_title": "Order Lines",
            "cancel_url": "salesorder_list",
        },
    )


@permission_required("sales.view_salesorder", raise_exception=True)
def salesorder_detail(request, pk):
    order = get_object_or_404(
        SalesOrder.objects.select_related("customer", "quotation", "warehouse"), pk=pk
    )
    actions = []
    if order.status in ("Draft", "Open"):
        actions.append(("Create Delivery", _action_url("delivery_create", query={"order": order.pk}), ""))
    if order.status in ("Draft", "Open"):
        actions.append(("Complete Order", _action_url("salesorder_complete", pk=order.pk), ""))
        actions.append(("Cancel Order", _action_url("salesorder_cancel", pk=order.pk), "btn-danger"))
    return render(
        request, "sales/doc_detail.html",
        {
            "doc": order,
            "doc_number": order.order_number,
            "info_fields": [
                ("Customer", order.customer.name),
                ("Date", order.order_date),
                ("Required By", order.required_date or "-"),
                ("Quotation", order.quotation.quotation_number if order.quotation else "-"),
                ("Warehouse", order.warehouse.name if order.warehouse else "-"),
                ("Status", order.get_status_display()),
                ("Remarks", order.remarks or "-"),
            ],
            "lines": order.lines.select_related("item"),
            "lines_title": "Order Lines",
            "total": order.total,
            "actions": actions,
            "list_url": "salesorder_list",
        },
    )


@permission_required("sales.change_salesorder", raise_exception=True)
def salesorder_update(request, pk):
    order = get_object_or_404(SalesOrder, pk=pk)
    if order.status not in ("Draft", "Open"):
        messages.error(request, "Only Draft or Open orders can be edited.")
        return redirect("salesorder_detail", pk=pk)
    old = _model_values(order)
    if request.method == "POST":
        form = SalesOrderForm(request.POST, instance=order)
        formset = SalesOrderLineFormSet(request.POST, instance=order)
        if form.is_valid() and formset.is_valid():
            obj = form.save()
            formset.save()
            log_activity(
                request.user, "Update Sales Order", app_label="sales",
                model_name="SalesOrder", object_id=obj.pk, object_repr=obj.order_number,
                old_values=old, new_values=_model_values(obj), request=request,
            )
            messages.success(request, "Order updated successfully.")
            return redirect("salesorder_detail", pk=pk)
    else:
        form = SalesOrderForm(instance=order)
        formset = SalesOrderLineFormSet(instance=order)
    return render(
        request, "sales/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": f"Edit Order: {order.order_number}",
            "lines_title": "Order Lines",
            "cancel_url": "salesorder_detail",
        },
    )


@permission_required("sales.change_salesorder", raise_exception=True)
def salesorder_complete(request, pk):
    order = get_object_or_404(SalesOrder, pk=pk)
    if order.status not in ("Draft", "Open"):
        messages.error(request, "Only Draft or Open orders can be completed.")
        return redirect("salesorder_detail", pk=pk)
    order.status = "Completed"
    order.save()
    log_activity(
        request.user, "Complete Sales Order", app_label="sales",
        model_name="SalesOrder", object_id=order.pk, object_repr=order.order_number,
        new_values={"status": "Completed"}, request=request,
    )
    messages.success(request, "Order completed.")
    return redirect("salesorder_detail", pk=pk)


@permission_required("sales.change_salesorder", raise_exception=True)
def salesorder_cancel(request, pk):
    order = get_object_or_404(SalesOrder, pk=pk)
    if order.status not in ("Draft", "Open"):
        messages.error(request, "Only Draft or Open orders can be cancelled.")
        return redirect("salesorder_detail", pk=pk)
    order.status = "Cancelled"
    order.save()
    log_activity(
        request.user, "Cancel Sales Order", app_label="sales",
        model_name="SalesOrder", object_id=order.pk, object_repr=order.order_number,
        new_values={"status": "Cancelled"}, request=request,
    )
    messages.success(request, "Order cancelled.")
    return redirect("salesorder_detail", pk=pk)


# ===================================================================
# Delivery (C)
# ===================================================================

@permission_required("sales.view_delivery", raise_exception=True)
def delivery_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    deliveries = Delivery.objects.select_related("customer", "warehouse", "order").order_by("-created_at")
    if query:
        deliveries = deliveries.filter(
            Q(delivery_number__icontains=query) | Q(customer__name__icontains=query)
        )
    if status:
        deliveries = deliveries.filter(status=status)
    paginator = Paginator(deliveries, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = _list_context(
        "Deliveries",
        [
            {"label": "Delivery #", "key": "delivery_number", "link": "delivery_detail"},
            {"label": "Customer", "key": "customer"},
            {"label": "Warehouse", "key": "warehouse"},
            {"label": "Date", "key": "delivery_date"},
            {"label": "Status", "key": "status"},
        ],
        "delivery_create",
        "delivery_detail",
        ["Draft", "Posted", "Cancelled"],
    )
    context.update({"page_obj": page_obj, "query": query, "status": status})
    return render(request, "sales/doc_list.html", context)


@permission_required("sales.add_delivery", raise_exception=True)
def delivery_create(request):
    """Create a Delivery, optionally from an Open Sales Order (?order=<id>)."""
    order = _get_or_none(SalesOrder, request.GET.get("order"))
    initial = {}
    line_initial = []
    if order:
        initial = {
            "customer": order.customer,
            "order": order,
            "warehouse": order.warehouse,
        }
        line_initial = [
            {
                "item": l.item_id,
                "quantity": l.quantity,
                "unit_price": l.unit_price,
                "discount_percent": l.discount_percent,
                "tax_percent": l.tax_percent,
            }
            for l in order.lines.all()
        ]

    if request.method == "POST":
        form = DeliveryForm(request.POST)
        formset = DeliveryLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            delivery = form.save(commit=False)
            delivery.created_by = request.user
            delivery.status = "Draft"
            delivery.save()
            formset.instance = delivery
            formset.save()
            log_activity(
                request.user, "Create Delivery", app_label="sales",
                model_name="Delivery", object_id=delivery.pk, object_repr=delivery.delivery_number,
                new_values={"delivery_number": delivery.delivery_number, "customer": str(delivery.customer)},
                request=request,
            )
            messages.success(request, f"Delivery {delivery.delivery_number} created (Draft).")
            return redirect("delivery_detail", pk=delivery.pk)
    else:
        form = DeliveryForm(initial=initial)
        formset = DeliveryLineFormSet(initial=line_initial)
    return render(
        request, "sales/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Create Delivery",
            "lines_title": "Delivery Lines",
            "cancel_url": "delivery_list",
        },
    )


@permission_required("sales.view_delivery", raise_exception=True)
def delivery_detail(request, pk):
    delivery = get_object_or_404(
        Delivery.objects.select_related("customer", "warehouse", "order"), pk=pk
    )
    actions = []
    if delivery.status == "Draft":
        actions.append(("Post Delivery", _action_url("delivery_post", pk=delivery.pk), ""))
        actions.append(("Cancel Delivery", _action_url("delivery_cancel", pk=delivery.pk), "btn-danger"))
    if delivery.status == "Posted":
        actions.append(("Create A/R Invoice", _action_url("arinvoice_create", query={"delivery": delivery.pk}), ""))
    return render(
        request, "sales/doc_detail.html",
        {
            "doc": delivery,
            "doc_number": delivery.delivery_number,
            "info_fields": [
                ("Customer", delivery.customer.name),
                ("Order", delivery.order.order_number if delivery.order else "-"),
                ("Warehouse", delivery.warehouse.name),
                ("Date", delivery.delivery_date),
                ("Status", delivery.get_status_display()),
                ("Remarks", delivery.remarks or "-"),
            ],
            "lines": delivery.lines.select_related("item"),
            "lines_title": "Delivery Lines",
            "total": delivery.total,
            "actions": actions,
            "list_url": "delivery_list",
        },
    )


@permission_required("sales.change_delivery", raise_exception=True)
def delivery_update(request, pk):
    delivery = get_object_or_404(Delivery, pk=pk)
    if delivery.status != "Draft":
        messages.error(request, "Only Draft deliveries can be edited.")
        return redirect("delivery_detail", pk=pk)
    old = _model_values(delivery)
    if request.method == "POST":
        form = DeliveryForm(request.POST, instance=delivery)
        formset = DeliveryLineFormSet(request.POST, instance=delivery)
        if form.is_valid() and formset.is_valid():
            obj = form.save()
            formset.save()
            log_activity(
                request.user, "Update Delivery", app_label="sales",
                model_name="Delivery", object_id=obj.pk, object_repr=obj.delivery_number,
                old_values=old, new_values=_model_values(obj), request=request,
            )
            messages.success(request, "Delivery updated successfully.")
            return redirect("delivery_detail", pk=pk)
    else:
        form = DeliveryForm(instance=delivery)
        formset = DeliveryLineFormSet(instance=delivery)
    return render(
        request, "sales/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": f"Edit Delivery: {delivery.delivery_number}",
            "lines_title": "Delivery Lines",
            "cancel_url": "delivery_detail",
        },
    )


@permission_required("sales.change_delivery", raise_exception=True)
def delivery_post(request, pk):
    """Post a Draft delivery: reduce inventory and record stock movement."""
    delivery = get_object_or_404(Delivery, pk=pk)
    if delivery.status != "Draft":
        messages.error(request, "Only Draft deliveries can be posted.")
        return redirect("delivery_detail", pk=pk)

    for line in delivery.lines.select_related("item"):
        stock = Stock.objects.filter(item=line.item, warehouse=delivery.warehouse).first()
        available = stock.quantity if stock else 0
        if available < line.quantity:
            messages.error(
                request,
                f"Insufficient stock for {line.item.name}: need {line.quantity}, have {available}.",
            )
            return redirect("delivery_detail", pk=pk)

    with transaction.atomic():
        for line in delivery.lines.select_related("item"):
            stock, _ = Stock.objects.get_or_create(
                item=line.item, warehouse=delivery.warehouse, defaults={"quantity": 0}
            )
            stock.quantity -= line.quantity
            stock.save()
            _record_stock_movement(
                line.item, delivery.warehouse, -line.quantity,
                "Sales Delivery", request.user, stock.quantity,
                reference_document="Delivery", reference_number=delivery.delivery_number,
            )
        delivery.status = "Posted"
        delivery.save()

    log_activity(
        request.user, "Post Delivery", app_label="sales",
        model_name="Delivery", object_id=delivery.pk, object_repr=delivery.delivery_number,
        new_values={"status": "Posted"}, request=request,
    )
    messages.success(request, "Delivery posted. Inventory has been reduced.")
    return redirect("delivery_detail", pk=pk)


@permission_required("sales.change_delivery", raise_exception=True)
def delivery_cancel(request, pk):
    delivery = get_object_or_404(Delivery, pk=pk)
    if delivery.status != "Draft":
        messages.error(request, "Only Draft deliveries can be cancelled.")
        return redirect("delivery_detail", pk=pk)
    delivery.status = "Cancelled"
    delivery.save()
    log_activity(
        request.user, "Cancel Delivery", app_label="sales",
        model_name="Delivery", object_id=delivery.pk, object_repr=delivery.delivery_number,
        new_values={"status": "Cancelled"}, request=request,
    )
    messages.success(request, "Delivery cancelled.")
    return redirect("delivery_detail", pk=pk)


# ===================================================================
# Return Request (D)
# ===================================================================

@permission_required("sales.view_returnrequest", raise_exception=True)
def returnrequest_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    requests = ReturnRequest.objects.select_related("customer").order_by("-created_at")
    if query:
        requests = requests.filter(
            Q(request_number__icontains=query) | Q(customer__name__icontains=query)
        )
    if status:
        requests = requests.filter(status=status)
    paginator = Paginator(requests, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = _list_context(
        "Return Requests",
        [
            {"label": "Request #", "key": "request_number", "link": "returnrequest_detail"},
            {"label": "Customer", "key": "customer"},
            {"label": "Date", "key": "request_date"},
            {"label": "Status", "key": "status"},
        ],
        "returnrequest_create",
        "returnrequest_detail",
        ["Open", "Approved", "Rejected", "Cancelled"],
    )
    context.update({"page_obj": page_obj, "query": query, "status": status})
    return render(request, "sales/doc_list.html", context)


@permission_required("sales.add_returnrequest", raise_exception=True)
def returnrequest_create(request):
    if request.method == "POST":
        form = ReturnRequestForm(request.POST)
        formset = ReturnRequestLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            formset.instance = obj
            formset.save()
            log_activity(
                request.user, "Create Return Request", app_label="sales",
                model_name="ReturnRequest", object_id=obj.pk, object_repr=obj.request_number,
                new_values={"request_number": obj.request_number, "customer": str(obj.customer)},
                request=request,
            )
            messages.success(request, f"Return request {obj.request_number} created.")
            return redirect("returnrequest_detail", pk=obj.pk)
    else:
        form = ReturnRequestForm()
        formset = ReturnRequestLineFormSet()
    return render(
        request, "sales/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Create Return Request",
            "lines_title": "Requested Lines",
            "show_reason": True,
            "cancel_url": "returnrequest_list",
        },
    )


@permission_required("sales.view_returnrequest", raise_exception=True)
def returnrequest_detail(request, pk):
    rr = get_object_or_404(ReturnRequest.objects.select_related("customer", "order"), pk=pk)
    actions = []
    if rr.status == "Open":
        actions.append(("Approve", _action_url("returnrequest_approve", pk=rr.pk), ""))
        actions.append(("Reject", _action_url("returnrequest_reject", pk=rr.pk), "btn-danger"))
    if rr.status == "Approved":
        actions.append(("Create Return", _action_url("salesreturn_create", query={"request": rr.pk}), ""))
    return render(
        request, "sales/doc_detail.html",
        {
            "doc": rr,
            "doc_number": rr.request_number,
            "info_fields": [
                ("Customer", rr.customer.name),
                ("Order", rr.order.order_number if rr.order else "-"),
                ("Date", rr.request_date),
                ("Status", rr.get_status_display()),
                ("Reason", rr.reason or "-"),
            ],
            "lines": rr.lines.select_related("item"),
            "lines_title": "Requested Lines",
            "total": rr.total,
            "actions": actions,
            "list_url": "returnrequest_list",
        },
    )


@permission_required("sales.change_returnrequest", raise_exception=True)
def returnrequest_approve(request, pk):
    rr = get_object_or_404(ReturnRequest, pk=pk)
    if rr.status != "Open":
        messages.error(request, "Only Open return requests can be approved.")
        return redirect("returnrequest_detail", pk=pk)
    rr.status = "Approved"
    rr.save()
    log_activity(
        request.user, "Approve Return Request", app_label="sales",
        model_name="ReturnRequest", object_id=rr.pk, object_repr=rr.request_number,
        new_values={"status": "Approved"}, request=request,
    )
    messages.success(request, "Return request approved.")
    return redirect("returnrequest_detail", pk=pk)


@permission_required("sales.change_returnrequest", raise_exception=True)
def returnrequest_reject(request, pk):
    rr = get_object_or_404(ReturnRequest, pk=pk)
    if rr.status != "Open":
        messages.error(request, "Only Open return requests can be rejected.")
        return redirect("returnrequest_detail", pk=pk)
    rr.status = "Rejected"
    rr.save()
    log_activity(
        request.user, "Reject Return Request", app_label="sales",
        model_name="ReturnRequest", object_id=rr.pk, object_repr=rr.request_number,
        new_values={"status": "Rejected"}, request=request,
    )
    messages.success(request, "Return request rejected.")
    return redirect("returnrequest_detail", pk=pk)


# ===================================================================
# Return (E)
# ===================================================================

@permission_required("sales.view_salesreturn", raise_exception=True)
def salesreturn_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    returns = SalesReturn.objects.select_related("customer", "warehouse").order_by("-created_at")
    if query:
        returns = returns.filter(
            Q(return_number__icontains=query) | Q(customer__name__icontains=query)
        )
    if status:
        returns = returns.filter(status=status)
    paginator = Paginator(returns, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = _list_context(
        "Returns",
        [
            {"label": "Return #", "key": "return_number", "link": "salesreturn_detail"},
            {"label": "Customer", "key": "customer"},
            {"label": "Warehouse", "key": "warehouse"},
            {"label": "Date", "key": "return_date"},
            {"label": "Status", "key": "status"},
        ],
        "salesreturn_create",
        "salesreturn_detail",
        ["Draft", "Posted", "Cancelled"],
    )
    context.update({"page_obj": page_obj, "query": query, "status": status})
    return render(request, "sales/doc_list.html", context)


@permission_required("sales.add_salesreturn", raise_exception=True)
def salesreturn_create(request):
    """Create a Return, optionally from an approved Return Request (?request=<id>)."""
    rreq = _get_or_none(ReturnRequest, request.GET.get("request"))
    initial = {}
    line_initial = []
    if rreq:
        initial = {"customer": rreq.customer, "request": rreq}
        line_initial = [
            {
                "item": l.item_id,
                "quantity": l.quantity,
                "unit_price": l.unit_price,
                "discount_percent": l.discount_percent,
                "tax_percent": l.tax_percent,
            }
            for l in rreq.lines.all()
        ]

    if request.method == "POST":
        form = SalesReturnForm(request.POST)
        formset = SalesReturnLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.status = "Draft"
            obj.save()
            formset.instance = obj
            formset.save()
            log_activity(
                request.user, "Create Return", app_label="sales",
                model_name="SalesReturn", object_id=obj.pk, object_repr=obj.return_number,
                new_values={"return_number": obj.return_number, "customer": str(obj.customer)},
                request=request,
            )
            messages.success(request, f"Return {obj.return_number} created (Draft).")
            return redirect("salesreturn_detail", pk=obj.pk)
    else:
        form = SalesReturnForm(initial=initial)
        formset = SalesReturnLineFormSet(initial=line_initial)
    return render(
        request, "sales/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Create Return",
            "lines_title": "Return Lines",
            "show_reason": True,
            "cancel_url": "salesreturn_list",
        },
    )


@permission_required("sales.view_salesreturn", raise_exception=True)
def salesreturn_detail(request, pk):
    ret = get_object_or_404(
        SalesReturn.objects.select_related("customer", "warehouse", "request"), pk=pk
    )
    actions = []
    if ret.status == "Draft":
        actions.append(("Post Return", _action_url("salesreturn_post", pk=ret.pk), ""))
        actions.append(("Cancel Return", _action_url("salesreturn_cancel", pk=ret.pk), "btn-danger"))
    if ret.status == "Posted":
        actions.append(("Create A/R Credit Memo", _action_url("arcreditmemo_create", query={"return": ret.pk}), ""))
    return render(
        request, "sales/doc_detail.html",
        {
            "doc": ret,
            "doc_number": ret.return_number,
            "info_fields": [
                ("Customer", ret.customer.name),
                ("Return Request", ret.request.request_number if ret.request else "-"),
                ("Warehouse", ret.warehouse.name),
                ("Date", ret.return_date),
                ("Status", ret.get_status_display()),
                ("Remarks", ret.remarks or "-"),
            ],
            "lines": ret.lines.select_related("item"),
            "lines_title": "Return Lines",
            "total": ret.total,
            "actions": actions,
            "list_url": "salesreturn_list",
        },
    )


@permission_required("sales.change_salesreturn", raise_exception=True)
def salesreturn_post(request, pk):
    """Post a Return: goods come back, inventory increases."""
    ret = get_object_or_404(SalesReturn, pk=pk)
    if ret.status != "Draft":
        messages.error(request, "Only Draft returns can be posted.")
        return redirect("salesreturn_detail", pk=pk)

    with transaction.atomic():
        for line in ret.lines.select_related("item"):
            stock, _ = Stock.objects.get_or_create(
                item=line.item, warehouse=ret.warehouse, defaults={"quantity": 0}
            )
            stock.quantity += line.quantity
            stock.save()
            _record_stock_movement(
                line.item, ret.warehouse, line.quantity,
                "Return", request.user, stock.quantity,
                reference_document="SalesReturn", reference_number=ret.return_number,
            )
        ret.status = "Posted"
        ret.save()

    log_activity(
        request.user, "Post Return", app_label="sales",
        model_name="SalesReturn", object_id=ret.pk, object_repr=ret.return_number,
        new_values={"status": "Posted"}, request=request,
    )
    messages.success(request, "Return posted. Inventory has been increased.")
    return redirect("salesreturn_detail", pk=pk)


@permission_required("sales.change_salesreturn", raise_exception=True)
def salesreturn_cancel(request, pk):
    ret = get_object_or_404(SalesReturn, pk=pk)
    if ret.status != "Draft":
        messages.error(request, "Only Draft returns can be cancelled.")
        return redirect("salesreturn_detail", pk=pk)
    ret.status = "Cancelled"
    ret.save()
    log_activity(
        request.user, "Cancel Return", app_label="sales",
        model_name="SalesReturn", object_id=ret.pk, object_repr=ret.return_number,
        new_values={"status": "Cancelled"}, request=request,
    )
    messages.success(request, "Return cancelled.")
    return redirect("salesreturn_detail", pk=pk)


# ===================================================================
# A/R Invoice (F)
# ===================================================================

@permission_required("sales.view_arinvoice", raise_exception=True)
def arinvoice_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    invoices = ARInvoice.objects.select_related("customer").order_by("-created_at")
    if query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=query) | Q(customer__name__icontains=query)
        )
    if status:
        invoices = invoices.filter(status=status)
    paginator = Paginator(invoices, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = _list_context(
        "A/R Invoices",
        [
            {"label": "Invoice #", "key": "invoice_number", "link": "arinvoice_detail"},
            {"label": "Customer", "key": "customer"},
            {"label": "Date", "key": "invoice_date"},
            {"label": "Status", "key": "status"},
        ],
        "arinvoice_create",
        "arinvoice_detail",
        ["Draft", "Open", "Partial", "Paid", "Cancelled"],
    )
    context.update({"page_obj": page_obj, "query": query, "status": status})
    return render(request, "sales/doc_list.html", context)


@permission_required("sales.add_arinvoice", raise_exception=True)
def arinvoice_create(request):
    """Create an A/R Invoice, optionally from a Posted Delivery (?delivery=<id>)."""
    delivery = _get_or_none(Delivery, request.GET.get("delivery"))
    initial = {}
    line_initial = []
    if delivery:
        initial = {"customer": delivery.customer, "delivery": delivery}
        line_initial = [
            {
                "item": l.item_id,
                "quantity": l.quantity,
                "unit_price": l.unit_price,
                "discount_percent": l.discount_percent,
                "tax_percent": l.tax_percent,
            }
            for l in delivery.lines.all()
        ]

    if request.method == "POST":
        form = ARInvoiceForm(request.POST)
        formset = ARInvoiceLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            invoice.created_by = request.user
            invoice.status = "Open"
            invoice.save()
            formset.instance = invoice
            formset.save()
            log_activity(
                request.user, "Create A/R Invoice", app_label="sales",
                model_name="ARInvoice", object_id=invoice.pk, object_repr=invoice.invoice_number,
                new_values={"invoice_number": invoice.invoice_number, "customer": str(invoice.customer)},
                request=request,
            )
            messages.success(request, f"A/R invoice {invoice.invoice_number} created.")
            return redirect("arinvoice_detail", pk=invoice.pk)
    else:
        form = ARInvoiceForm(initial=initial)
        formset = ARInvoiceLineFormSet(initial=line_initial)
    return render(
        request, "sales/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Create A/R Invoice",
            "lines_title": "Invoice Lines",
            "cancel_url": "arinvoice_list",
        },
    )


@permission_required("sales.view_arinvoice", raise_exception=True)
def arinvoice_detail(request, pk):
    invoice = get_object_or_404(
        ARInvoice.objects.select_related("customer", "order", "delivery"), pk=pk
    )
    actions = []
    if invoice.status in ("Draft", "Open"):
        actions.append(("Create Incoming Payment", _action_url("incomingpayment_create", query={"invoice": invoice.pk}), ""))
        actions.append(("Cancel Invoice", _action_url("arinvoice_cancel", pk=invoice.pk), "btn-danger"))
    return render(
        request, "sales/doc_detail.html",
        {
            "doc": invoice,
            "doc_number": invoice.invoice_number,
            "info_fields": [
                ("Customer", invoice.customer.name),
                ("Date", invoice.invoice_date),
                ("Due Date", invoice.due_date or "-"),
                ("Status", invoice.get_status_display()),
                ("Paid Amount", invoice.paid_amount),
                ("Balance", invoice.balance),
                ("Remarks", invoice.remarks or "-"),
            ],
            "lines": invoice.lines.select_related("item"),
            "lines_title": "Invoice Lines",
            "total": invoice.total,
            "actions": actions,
            "list_url": "arinvoice_list",
        },
    )


@permission_required("sales.change_arinvoice", raise_exception=True)
def arinvoice_cancel(request, pk):
    invoice = get_object_or_404(ARInvoice, pk=pk)
    if invoice.status not in ("Draft", "Open"):
        messages.error(request, "Only Draft or Open invoices can be cancelled.")
        return redirect("arinvoice_detail", pk=pk)
    invoice.status = "Cancelled"
    invoice.save()
    log_activity(
        request.user, "Cancel A/R Invoice", app_label="sales",
        model_name="ARInvoice", object_id=invoice.pk, object_repr=invoice.invoice_number,
        new_values={"status": "Cancelled"}, request=request,
    )
    messages.success(request, "Invoice cancelled.")
    return redirect("arinvoice_detail", pk=pk)


# ===================================================================
# A/R Credit Memo (G)
# ===================================================================

@permission_required("sales.view_arcreditmemo", raise_exception=True)
def arcreditmemo_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    memos = ARCreditMemo.objects.select_related("customer").order_by("-created_at")
    if query:
        memos = memos.filter(
            Q(credit_memo_number__icontains=query) | Q(customer__name__icontains=query)
        )
    if status:
        memos = memos.filter(status=status)
    paginator = Paginator(memos, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = _list_context(
        "A/R Credit Memos",
        [
            {"label": "Memo #", "key": "credit_memo_number", "link": "arcreditmemo_detail"},
            {"label": "Customer", "key": "customer"},
            {"label": "Date", "key": "credit_date"},
            {"label": "Status", "key": "status"},
        ],
        "arcreditmemo_create",
        "arcreditmemo_detail",
        ["Draft", "Open", "Applied", "Cancelled"],
    )
    context.update({"page_obj": page_obj, "query": query, "status": status})
    return render(request, "sales/doc_list.html", context)


@permission_required("sales.add_arcreditmemo", raise_exception=True)
def arcreditmemo_create(request):
    """Create an A/R Credit Memo, optionally from a Posted Return (?return=<id>)."""
    ret = _get_or_none(SalesReturn, request.GET.get("return"))
    initial = {}
    line_initial = []
    if ret:
        initial = {"customer": ret.customer, "return_doc": ret}
        line_initial = [
            {
                "item": l.item_id,
                "quantity": l.quantity,
                "unit_price": l.unit_price,
                "discount_percent": l.discount_percent,
                "tax_percent": l.tax_percent,
            }
            for l in ret.lines.all()
        ]

    if request.method == "POST":
        form = ARCreditMemoForm(request.POST)
        formset = ARCreditMemoLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            memo = form.save(commit=False)
            memo.created_by = request.user
            memo.status = "Open"
            memo.save()
            formset.instance = memo
            formset.save()
            log_activity(
                request.user, "Create A/R Credit Memo", app_label="sales",
                model_name="ARCreditMemo", object_id=memo.pk, object_repr=memo.credit_memo_number,
                new_values={"credit_memo_number": memo.credit_memo_number, "customer": str(memo.customer)},
                request=request,
            )
            messages.success(request, f"Credit memo {memo.credit_memo_number} created.")
            return redirect("arcreditmemo_detail", pk=memo.pk)
    else:
        form = ARCreditMemoForm(initial=initial)
        formset = ARCreditMemoLineFormSet(initial=line_initial)
    return render(
        request, "sales/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Create A/R Credit Memo",
            "lines_title": "Credit Memo Lines",
            "cancel_url": "arcreditmemo_list",
        },
    )


@permission_required("sales.view_arcreditmemo", raise_exception=True)
def arcreditmemo_detail(request, pk):
    memo = get_object_or_404(
        ARCreditMemo.objects.select_related("customer", "return_doc"), pk=pk
    )
    actions = []
    if memo.status == "Open":
        actions.append(("Apply Memo", _action_url("arcreditmemo_apply", pk=memo.pk), ""))
        actions.append(("Cancel Memo", _action_url("arcreditmemo_cancel", pk=memo.pk), "btn-danger"))
    return render(
        request, "sales/doc_detail.html",
        {
            "doc": memo,
            "doc_number": memo.credit_memo_number,
            "info_fields": [
                ("Customer", memo.customer.name),
                ("Return", memo.return_doc.return_number if memo.return_doc else "-"),
                ("Date", memo.credit_date),
                ("Status", memo.get_status_display()),
                ("Remarks", memo.remarks or "-"),
            ],
            "lines": memo.lines.select_related("item"),
            "lines_title": "Credit Memo Lines",
            "total": memo.total,
            "actions": actions,
            "list_url": "arcreditmemo_list",
        },
    )


@permission_required("sales.change_arcreditmemo", raise_exception=True)
def arcreditmemo_apply(request, pk):
    memo = get_object_or_404(ARCreditMemo, pk=pk)
    if memo.status != "Open":
        messages.error(request, "Only Open credit memos can be applied.")
        return redirect("arcreditmemo_detail", pk=pk)
    memo.status = "Applied"
    memo.save()
    log_activity(
        request.user, "Apply A/R Credit Memo", app_label="sales",
        model_name="ARCreditMemo", object_id=memo.pk, object_repr=memo.credit_memo_number,
        new_values={"status": "Applied"}, request=request,
    )
    messages.success(request, "Credit memo applied. Customer receivable reduced.")
    return redirect("arcreditmemo_detail", pk=pk)


@permission_required("sales.change_arcreditmemo", raise_exception=True)
def arcreditmemo_cancel(request, pk):
    memo = get_object_or_404(ARCreditMemo, pk=pk)
    if memo.status not in ("Draft", "Open"):
        messages.error(request, "Only Draft or Open credit memos can be cancelled.")
        return redirect("arcreditmemo_detail", pk=pk)
    memo.status = "Cancelled"
    memo.save()
    log_activity(
        request.user, "Cancel A/R Credit Memo", app_label="sales",
        model_name="ARCreditMemo", object_id=memo.pk, object_repr=memo.credit_memo_number,
        new_values={"status": "Cancelled"}, request=request,
    )
    messages.success(request, "Credit memo cancelled.")
    return redirect("arcreditmemo_detail", pk=pk)


# ===================================================================
# Incoming Payment (H)
# ===================================================================

@permission_required("sales.view_incomingpayment", raise_exception=True)
def incomingpayment_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    payments = IncomingPayment.objects.select_related("customer", "invoice").order_by("-created_at")
    if query:
        payments = payments.filter(
            Q(payment_number__icontains=query) | Q(customer__name__icontains=query)
        )
    if status:
        payments = payments.filter(status=status)
    paginator = Paginator(payments, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = _list_context(
        "Incoming Payments",
        [
            {"label": "Payment #", "key": "payment_number", "link": "incomingpayment_detail"},
            {"label": "Customer", "key": "customer"},
            {"label": "Date", "key": "payment_date"},
            {"label": "Amount", "key": "amount"},
            {"label": "Status", "key": "status"},
        ],
        "incomingpayment_create",
        "incomingpayment_detail",
        ["Draft", "Completed", "Cancelled"],
    )
    context.update({"page_obj": page_obj, "query": query, "status": status})
    return render(request, "sales/doc_list.html", context)


@permission_required("sales.add_incomingpayment", raise_exception=True)
def incomingpayment_create(request):
    """Create an Incoming Payment, optionally for an Open A/R Invoice (?invoice=<id>)."""
    invoice = _get_or_none(ARInvoice, request.GET.get("invoice"))
    initial = {}
    if invoice:
        initial = {"customer": invoice.customer, "invoice": invoice, "amount": invoice.balance}

    if request.method == "POST":
        form = IncomingPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.created_by = request.user
            payment.status = "Draft"
            payment.save()
            log_activity(
                request.user, "Create Incoming Payment", app_label="sales",
                model_name="IncomingPayment", object_id=payment.pk, object_repr=payment.payment_number,
                new_values={"payment_number": payment.payment_number, "amount": str(payment.amount)},
                request=request,
            )
            messages.success(request, f"Payment {payment.payment_number} created (Draft).")
            return redirect("incomingpayment_detail", pk=payment.pk)
    else:
        form = IncomingPaymentForm(initial=initial)
    return render(
        request, "sales/incomingpayment_form.html",
        {"form": form, "title": "Create Incoming Payment"},
    )


@permission_required("sales.view_incomingpayment", raise_exception=True)
def incomingpayment_detail(request, pk):
    payment = get_object_or_404(
        IncomingPayment.objects.select_related("customer", "invoice"), pk=pk
    )
    actions = []
    if payment.status == "Draft":
        actions.append(("Complete Payment", _action_url("incomingpayment_complete", pk=payment.pk), ""))
        actions.append(("Cancel Payment", _action_url("incomingpayment_cancel", pk=payment.pk), "btn-danger"))
    return render(
        request, "sales/incomingpayment_detail.html",
        {
            "payment": payment,
            "doc": payment,
            "doc_number": payment.payment_number,
            "info_fields": [
                ("Customer", payment.customer.name),
                ("Invoice", payment.invoice.invoice_number if payment.invoice else "-"),
                ("Date", payment.payment_date),
                ("Amount", payment.amount),
                ("Method", payment.payment_method),
                ("Reference", payment.reference or "-"),
                ("Status", payment.get_status_display()),
            ],
            "actions": actions,
            "list_url": "incomingpayment_list",
        },
    )


@permission_required("sales.change_incomingpayment", raise_exception=True)
def incomingpayment_complete(request, pk):
    """Complete the payment and update the invoice balance."""
    payment = get_object_or_404(IncomingPayment, pk=pk)
    if payment.status != "Draft":
        messages.error(request, "Only Draft payments can be completed.")
        return redirect("incomingpayment_detail", pk=pk)

    with transaction.atomic():
        payment.status = "Completed"
        payment.save()
        if payment.invoice:
            invoice = payment.invoice
            balance = invoice.total - invoice.paid_amount
            invoice.status = "Paid" if balance <= 0 else "Partial"
            invoice.save(update_fields=["status"])

    log_activity(
        request.user, "Complete Incoming Payment", app_label="sales",
        model_name="IncomingPayment", object_id=payment.pk, object_repr=payment.payment_number,
        new_values={"status": "Completed", "amount": str(payment.amount)}, request=request,
    )
    messages.success(request, "Payment completed. Customer receivable updated.")
    return redirect("incomingpayment_detail", pk=pk)


@permission_required("sales.change_incomingpayment", raise_exception=True)
def incomingpayment_cancel(request, pk):
    payment = get_object_or_404(IncomingPayment, pk=pk)
    if payment.status != "Draft":
        messages.error(request, "Only Draft payments can be cancelled.")
        return redirect("incomingpayment_detail", pk=pk)
    payment.status = "Cancelled"
    payment.save()
    log_activity(
        request.user, "Cancel Incoming Payment", app_label="sales",
        model_name="IncomingPayment", object_id=payment.pk, object_repr=payment.payment_number,
        new_values={"status": "Cancelled"}, request=request,
    )
    messages.success(request, "Payment cancelled.")
    return redirect("incomingpayment_detail", pk=pk)
