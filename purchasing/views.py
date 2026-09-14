from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404

from audit.log import log_activity
from inventory.models import Stock

from .forms import (
    APCreditMemoForm,
    APCreditMemoLineFormSet,
    APInvoiceForm,
    APInvoiceLineFormSet,
    GoodsReceiptForm,
    GoodsReceiptLineFormSet,
    OutgoingPaymentForm,
    PurchaseOrderForm,
    PurchaseOrderLineFormSet,
    PurchaseQuotationForm,
    PurchaseQuotationLineFormSet,
    PurchaseRequestForm,
    PurchaseRequestLineFormSet,
    SupplierForm,
)
from .models import (
    APCreditMemo,
    APInvoice,
    GoodsReceipt,
    OutgoingPayment,
    PurchaseOrder,
    PurchaseQuotation,
    PurchaseRequest,
    Supplier,
)
from common.utils import (
    model_values as _model_values,
    get_or_none as _get_or_none,
    list_context as _list_context,
    action_url as _action_url,
)
from inventory.services import record_stock_movement as _record_stock_movement


# ===================================================================
# Suppliers
# ===================================================================

@permission_required("purchasing.view_supplier", raise_exception=True)
def supplier_list(request):
    query = request.GET.get("q", "")
    suppliers = Supplier.objects.all().order_by("name")
    if query:
        suppliers = suppliers.filter(
            Q(name__icontains=query)
            | Q(supplier_code__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query)
        )
    paginator = Paginator(suppliers, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "purchasing/supplier_list.html",
        {"page_obj": page_obj, "query": query},
    )


@permission_required("purchasing.add_supplier", raise_exception=True)
def supplier_create(request):
    if request.method == "POST":
        form = SupplierForm(request.POST)
        if form.is_valid():
            obj = form.save()
            log_activity(
                request.user, "Create Supplier", app_label="purchasing",
                model_name="Supplier", object_id=obj.pk, object_repr=obj.name,
                new_values=_model_values(obj), request=request,
            )
            messages.success(request, "Supplier added successfully.")
            return redirect("supplier_list")
    else:
        form = SupplierForm()
    return render(request, "purchasing/supplier_form.html", {"form": form, "title": "Add Supplier"})


@permission_required("purchasing.change_supplier", raise_exception=True)
def supplier_update(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    old = _model_values(supplier)
    if request.method == "POST":
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            obj = form.save()
            log_activity(
                request.user, "Update Supplier", app_label="purchasing",
                model_name="Supplier", object_id=obj.pk, object_repr=obj.name,
                old_values=old, new_values=_model_values(obj), request=request,
            )
            messages.success(request, "Supplier updated successfully.")
            return redirect("supplier_list")
    else:
        form = SupplierForm(instance=supplier)
    return render(
        request, "purchasing/supplier_form.html",
        {"form": form, "title": f"Edit Supplier: {supplier.name}"},
    )


@permission_required("purchasing.delete_supplier", raise_exception=True)
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == "POST":
        log_activity(
            request.user, "Delete Supplier", app_label="purchasing",
            model_name="Supplier", object_id=supplier.pk, object_repr=supplier.name,
            request=request,
        )
        supplier.delete()
        messages.success(request, "Supplier deleted successfully.")
        return redirect("supplier_list")
    return render(request, "purchasing/supplier_confirm_delete.html", {"supplier": supplier})


# ===================================================================
# Purchase Request (A)
# ===================================================================

@permission_required("purchasing.view_purchaserequest", raise_exception=True)
def purchaserequest_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    items = PurchaseRequest.objects.order_by("-created_at")
    if query:
        items = items.filter(
            Q(request_number__icontains=query)
            | Q(requested_by_name__icontains=query)
            | Q(department__icontains=query)
        )
    if status:
        items = items.filter(status=status)
    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = _list_context(
        "Purchase Requests",
        [
            {"label": "Request #", "key": "request_number", "link": "purchaserequest_detail"},
            {"label": "Requested By", "key": "requested_by_name"},
            {"label": "Department", "key": "department"},
            {"label": "Date", "key": "request_date"},
            {"label": "Status", "key": "status"},
        ],
        "purchaserequest_create",
        "purchaserequest_detail",
        ["Open", "Approved", "Rejected", "Cancelled"],
    )
    context.update({"page_obj": page_obj, "query": query, "status": status})
    return render(request, "purchasing/doc_list.html", context)


@permission_required("purchasing.add_purchaserequest", raise_exception=True)
def purchaserequest_create(request):
    if request.method == "POST":
        form = PurchaseRequestForm(request.POST)
        formset = PurchaseRequestLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.save()
            formset.instance = obj
            formset.save()
            log_activity(
                request.user, "Create Purchase Request", app_label="purchasing",
                model_name="PurchaseRequest", object_id=obj.pk, object_repr=obj.request_number,
                new_values={"request_number": obj.request_number, "department": obj.department},
                request=request,
            )
            messages.success(request, f"Purchase request {obj.request_number} created.")
            return redirect("purchaserequest_detail", pk=obj.pk)
    else:
        form = PurchaseRequestForm()
        formset = PurchaseRequestLineFormSet()
    return render(
        request, "purchasing/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Create Purchase Request",
            "lines_title": "Requested Lines",
            "show_reason": True,
            "cancel_url": "purchaserequest_list",
        },
    )


@permission_required("purchasing.view_purchaserequest", raise_exception=True)
def purchaserequest_detail(request, pk):
    obj = get_object_or_404(PurchaseRequest, pk=pk)
    actions = []
    if obj.status == "Open":
        actions.append(("Approve", _action_url("purchaserequest_approve", pk=obj.pk), ""))
        actions.append(("Reject", _action_url("purchaserequest_reject", pk=obj.pk), "btn-danger"))
    if obj.status in ("Open", "Approved"):
        actions.append(("Create Purchase Quotation", _action_url("purchasequotation_create", query={"request": obj.pk}), ""))
    return render(
        request, "purchasing/doc_detail.html",
        {
            "doc": obj,
            "doc_number": obj.request_number,
            "info_fields": [
                ("Requested By", obj.requested_by_name or "-"),
                ("Department", obj.department or "-"),
                ("Date", obj.request_date),
                ("Required By", obj.required_date or "-"),
                ("Status", obj.get_status_display()),
                ("Remarks", obj.remarks or "-"),
            ],
            "lines": obj.lines.select_related("item"),
            "lines_title": "Requested Lines",
            "total": obj.total,
            "actions": actions,
            "list_url": "purchaserequest_list",
        },
    )


@permission_required("purchasing.change_purchaserequest", raise_exception=True)
def purchaserequest_approve(request, pk):
    obj = get_object_or_404(PurchaseRequest, pk=pk)
    if obj.status != "Open":
        messages.error(request, "Only Open purchase requests can be approved.")
        return redirect("purchaserequest_detail", pk=pk)
    obj.status = "Approved"
    obj.save()
    log_activity(
        request.user, "Approve Purchase Request", app_label="purchasing",
        model_name="PurchaseRequest", object_id=obj.pk, object_repr=obj.request_number,
        new_values={"status": "Approved"}, request=request,
    )
    messages.success(request, "Purchase request approved.")
    return redirect("purchaserequest_detail", pk=pk)


@permission_required("purchasing.change_purchaserequest", raise_exception=True)
def purchaserequest_reject(request, pk):
    obj = get_object_or_404(PurchaseRequest, pk=pk)
    if obj.status != "Open":
        messages.error(request, "Only Open purchase requests can be rejected.")
        return redirect("purchaserequest_detail", pk=pk)
    obj.status = "Rejected"
    obj.save()
    log_activity(
        request.user, "Reject Purchase Request", app_label="purchasing",
        model_name="PurchaseRequest", object_id=obj.pk, object_repr=obj.request_number,
        new_values={"status": "Rejected"}, request=request,
    )
    messages.success(request, "Purchase request rejected.")
    return redirect("purchaserequest_detail", pk=pk)


# ===================================================================
# Purchase Quotation (B)
# ===================================================================

@permission_required("purchasing.view_purchasequotation", raise_exception=True)
def purchasequotation_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    items = PurchaseQuotation.objects.select_related("supplier").order_by("-created_at")
    if query:
        items = items.filter(
            Q(quotation_number__icontains=query) | Q(supplier__name__icontains=query)
        )
    if status:
        items = items.filter(status=status)
    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = _list_context(
        "Purchase Quotations",
        [
            {"label": "Quotation #", "key": "quotation_number", "link": "purchasequotation_detail"},
            {"label": "Supplier", "key": "supplier"},
            {"label": "Date", "key": "quotation_date"},
            {"label": "Status", "key": "status"},
        ],
        "purchasequotation_create",
        "purchasequotation_detail",
        ["Draft", "Open", "Accepted", "Rejected", "Cancelled"],
    )
    context.update({"page_obj": page_obj, "query": query, "status": status})
    return render(request, "purchasing/doc_list.html", context)


@permission_required("purchasing.add_purchasequotation", raise_exception=True)
def purchasequotation_create(request):
    """Create a Purchase Quotation, optionally from an Approved Purchase Request (?request=<id>)."""
    rreq = _get_or_none(PurchaseRequest, request.GET.get("request"))
    initial = {}
    line_initial = []
    if rreq:
        initial = {"request": rreq}
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
        form = PurchaseQuotationForm(request.POST)
        formset = PurchaseQuotationLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.status = "Open"
            obj.save()
            formset.instance = obj
            formset.save()
            log_activity(
                request.user, "Create Purchase Quotation", app_label="purchasing",
                model_name="PurchaseQuotation", object_id=obj.pk, object_repr=obj.quotation_number,
                new_values={"quotation_number": obj.quotation_number, "supplier": str(obj.supplier)},
                request=request,
            )
            messages.success(request, f"Purchase quotation {obj.quotation_number} created.")
            return redirect("purchasequotation_detail", pk=obj.pk)
    else:
        form = PurchaseQuotationForm(initial=initial)
        formset = PurchaseQuotationLineFormSet(initial=line_initial)
    return render(
        request, "purchasing/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Create Purchase Quotation",
            "lines_title": "Quotation Lines",
            "cancel_url": "purchasequotation_list",
        },
    )


@permission_required("purchasing.view_purchasequotation", raise_exception=True)
def purchasequotation_detail(request, pk):
    obj = get_object_or_404(
        PurchaseQuotation.objects.select_related("supplier", "request"), pk=pk
    )
    actions = []
    if obj.status == "Open":
        actions.append(("Accept Quotation", _action_url("purchasequotation_accept", pk=obj.pk), ""))
        actions.append(("Reject Quotation", _action_url("purchasequotation_reject", pk=obj.pk), "btn-danger"))
    if obj.status == "Accepted":
        actions.append(("Create Purchase Order", _action_url("purchaseorder_create", query={"quotation": obj.pk}), ""))
    return render(
        request, "purchasing/doc_detail.html",
        {
            "doc": obj,
            "doc_number": obj.quotation_number,
            "info_fields": [
                ("Supplier", obj.supplier.name),
                ("Purchase Request", obj.request.request_number if obj.request else "-"),
                ("Date", obj.quotation_date),
                ("Valid Until", obj.valid_until or "-"),
                ("Status", obj.get_status_display()),
                ("Remarks", obj.remarks or "-"),
            ],
            "lines": obj.lines.select_related("item"),
            "lines_title": "Quotation Lines",
            "total": obj.total,
            "actions": actions,
            "list_url": "purchasequotation_list",
        },
    )


@permission_required("purchasing.change_purchasequotation", raise_exception=True)
def purchasequotation_accept(request, pk):
    obj = get_object_or_404(PurchaseQuotation, pk=pk)
    if obj.status != "Open":
        messages.error(request, "Only Open quotations can be accepted.")
        return redirect("purchasequotation_detail", pk=pk)
    obj.status = "Accepted"
    obj.save()
    log_activity(
        request.user, "Accept Purchase Quotation", app_label="purchasing",
        model_name="PurchaseQuotation", object_id=obj.pk, object_repr=obj.quotation_number,
        new_values={"status": "Accepted"}, request=request,
    )
    messages.success(request, "Quotation accepted. You can now create a Purchase Order.")
    return redirect("purchasequotation_detail", pk=pk)


@permission_required("purchasing.change_purchasequotation", raise_exception=True)
def purchasequotation_reject(request, pk):
    obj = get_object_or_404(PurchaseQuotation, pk=pk)
    if obj.status != "Open":
        messages.error(request, "Only Open quotations can be rejected.")
        return redirect("purchasequotation_detail", pk=pk)
    obj.status = "Rejected"
    obj.save()
    log_activity(
        request.user, "Reject Purchase Quotation", app_label="purchasing",
        model_name="PurchaseQuotation", object_id=obj.pk, object_repr=obj.quotation_number,
        new_values={"status": "Rejected"}, request=request,
    )
    messages.success(request, "Quotation rejected.")
    return redirect("purchasequotation_detail", pk=pk)


# ===================================================================
# Purchase Order (C)
# ===================================================================

@permission_required("purchasing.view_purchaseorder", raise_exception=True)
def purchaseorder_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    items = PurchaseOrder.objects.select_related("supplier").order_by("-created_at")
    if query:
        items = items.filter(
            Q(order_number__icontains=query) | Q(supplier__name__icontains=query)
        )
    if status:
        items = items.filter(status=status)
    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = _list_context(
        "Purchase Orders",
        [
            {"label": "Order #", "key": "order_number", "link": "purchaseorder_detail"},
            {"label": "Supplier", "key": "supplier"},
            {"label": "Date", "key": "order_date"},
            {"label": "Status", "key": "status"},
        ],
        "purchaseorder_create",
        "purchaseorder_detail",
        ["Draft", "Open", "Completed", "Cancelled"],
    )
    context.update({"page_obj": page_obj, "query": query, "status": status})
    return render(request, "purchasing/doc_list.html", context)


@permission_required("purchasing.add_purchaseorder", raise_exception=True)
def purchaseorder_create(request):
    """Create a Purchase Order, optionally from an Accepted Purchase Quotation (?quotation=<id>)."""
    quotation = _get_or_none(PurchaseQuotation, request.GET.get("quotation"))
    initial = {}
    line_initial = []
    if quotation:
        initial = {"supplier": quotation.supplier, "quotation": quotation}
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
        form = PurchaseOrderForm(request.POST)
        formset = PurchaseOrderLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.status = "Open"
            obj.save()
            formset.instance = obj
            formset.save()
            log_activity(
                request.user, "Create Purchase Order", app_label="purchasing",
                model_name="PurchaseOrder", object_id=obj.pk, object_repr=obj.order_number,
                new_values={"order_number": obj.order_number, "supplier": str(obj.supplier)},
                request=request,
            )
            messages.success(request, f"Purchase order {obj.order_number} created.")
            return redirect("purchaseorder_detail", pk=obj.pk)
    else:
        form = PurchaseOrderForm(initial=initial)
        formset = PurchaseOrderLineFormSet(initial=line_initial)
    return render(
        request, "purchasing/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Create Purchase Order",
            "lines_title": "Order Lines",
            "cancel_url": "purchaseorder_list",
        },
    )


@permission_required("purchasing.view_purchaseorder", raise_exception=True)
def purchaseorder_detail(request, pk):
    obj = get_object_or_404(
        PurchaseOrder.objects.select_related("supplier", "quotation", "warehouse"), pk=pk
    )
    actions = []
    if obj.status in ("Draft", "Open"):
        actions.append(("Create Goods Receipt", _action_url("goodsreceipt_create", query={"order": obj.pk}), ""))
    if obj.status in ("Draft", "Open"):
        actions.append(("Complete Order", _action_url("purchaseorder_complete", pk=obj.pk), ""))
        actions.append(("Cancel Order", _action_url("purchaseorder_cancel", pk=obj.pk), "btn-danger"))
    return render(
        request, "purchasing/doc_detail.html",
        {
            "doc": obj,
            "doc_number": obj.order_number,
            "info_fields": [
                ("Supplier", obj.supplier.name),
                ("Quotation", obj.quotation.quotation_number if obj.quotation else "-"),
                ("Warehouse", obj.warehouse.name if obj.warehouse else "-"),
                ("Date", obj.order_date),
                ("Expected By", obj.expected_date or "-"),
                ("Status", obj.get_status_display()),
                ("Remarks", obj.remarks or "-"),
            ],
            "lines": obj.lines.select_related("item"),
            "lines_title": "Order Lines",
            "total": obj.total,
            "actions": actions,
            "list_url": "purchaseorder_list",
        },
    )


@permission_required("purchasing.change_purchaseorder", raise_exception=True)
def purchaseorder_complete(request, pk):
    obj = get_object_or_404(PurchaseOrder, pk=pk)
    if obj.status not in ("Draft", "Open"):
        messages.error(request, "Only Draft or Open orders can be completed.")
        return redirect("purchaseorder_detail", pk=pk)
    obj.status = "Completed"
    obj.save()
    log_activity(
        request.user, "Complete Purchase Order", app_label="purchasing",
        model_name="PurchaseOrder", object_id=obj.pk, object_repr=obj.order_number,
        new_values={"status": "Completed"}, request=request,
    )
    messages.success(request, "Purchase order completed.")
    return redirect("purchaseorder_detail", pk=pk)


@permission_required("purchasing.change_purchaseorder", raise_exception=True)
def purchaseorder_cancel(request, pk):
    obj = get_object_or_404(PurchaseOrder, pk=pk)
    if obj.status not in ("Draft", "Open"):
        messages.error(request, "Only Draft or Open orders can be cancelled.")
        return redirect("purchaseorder_detail", pk=pk)
    obj.status = "Cancelled"
    obj.save()
    log_activity(
        request.user, "Cancel Purchase Order", app_label="purchasing",
        model_name="PurchaseOrder", object_id=obj.pk, object_repr=obj.order_number,
        new_values={"status": "Cancelled"}, request=request,
    )
    messages.success(request, "Purchase order cancelled.")
    return redirect("purchaseorder_detail", pk=pk)


# ===================================================================
# Goods Receipt PO (D)
# ===================================================================

@permission_required("purchasing.view_goodsreceipt", raise_exception=True)
def goodsreceipt_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    items = GoodsReceipt.objects.select_related("supplier", "warehouse").order_by("-created_at")
    if query:
        items = items.filter(
            Q(receipt_number__icontains=query) | Q(supplier__name__icontains=query)
        )
    if status:
        items = items.filter(status=status)
    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = _list_context(
        "Goods Receipts (PO)",
        [
            {"label": "Receipt #", "key": "receipt_number", "link": "goodsreceipt_detail"},
            {"label": "Supplier", "key": "supplier"},
            {"label": "Warehouse", "key": "warehouse"},
            {"label": "Date", "key": "receipt_date"},
            {"label": "Status", "key": "status"},
        ],
        "goodsreceipt_create",
        "goodsreceipt_detail",
        ["Draft", "Posted", "Cancelled"],
    )
    context.update({"page_obj": page_obj, "query": query, "status": status})
    return render(request, "purchasing/doc_list.html", context)


@permission_required("purchasing.add_goodsreceipt", raise_exception=True)
def goodsreceipt_create(request):
    """Create a Goods Receipt, optionally from an Open Purchase Order (?order=<id>)."""
    order = _get_or_none(PurchaseOrder, request.GET.get("order"))
    initial = {}
    line_initial = []
    if order:
        initial = {"supplier": order.supplier, "order": order, "warehouse": order.warehouse}
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
        form = GoodsReceiptForm(request.POST)
        formset = GoodsReceiptLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.status = "Draft"
            obj.save()
            formset.instance = obj
            formset.save()
            log_activity(
                request.user, "Create Goods Receipt", app_label="purchasing",
                model_name="GoodsReceipt", object_id=obj.pk, object_repr=obj.receipt_number,
                new_values={"receipt_number": obj.receipt_number, "supplier": str(obj.supplier)},
                request=request,
            )
            messages.success(request, f"Goods receipt {obj.receipt_number} created (Draft).")
            return redirect("goodsreceipt_detail", pk=obj.pk)
    else:
        form = GoodsReceiptForm(initial=initial)
        formset = GoodsReceiptLineFormSet(initial=line_initial)
    return render(
        request, "purchasing/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Create Goods Receipt",
            "lines_title": "Receipt Lines",
            "cancel_url": "goodsreceipt_list",
        },
    )


@permission_required("purchasing.view_goodsreceipt", raise_exception=True)
def goodsreceipt_detail(request, pk):
    obj = get_object_or_404(
        GoodsReceipt.objects.select_related("supplier", "warehouse", "order"), pk=pk
    )
    actions = []
    if obj.status == "Draft":
        actions.append(("Post Goods Receipt", _action_url("goodsreceipt_post", pk=obj.pk), ""))
        actions.append(("Cancel Receipt", _action_url("goodsreceipt_cancel", pk=obj.pk), "btn-danger"))
    if obj.status == "Posted":
        actions.append(("Create A/P Invoice", _action_url("apinvoice_create", query={"receipt": obj.pk}), ""))
    return render(
        request, "purchasing/doc_detail.html",
        {
            "doc": obj,
            "doc_number": obj.receipt_number,
            "info_fields": [
                ("Supplier", obj.supplier.name),
                ("Purchase Order", obj.order.order_number if obj.order else "-"),
                ("Warehouse", obj.warehouse.name),
                ("Date", obj.receipt_date),
                ("Status", obj.get_status_display()),
                ("Remarks", obj.remarks or "-"),
            ],
            "lines": obj.lines.select_related("item"),
            "lines_title": "Receipt Lines",
            "total": obj.total,
            "actions": actions,
            "list_url": "goodsreceipt_list",
        },
    )


@permission_required("purchasing.change_goodsreceipt", raise_exception=True)
def goodsreceipt_post(request, pk):
    """Post a Draft goods receipt: goods arrive, inventory increases."""
    obj = get_object_or_404(GoodsReceipt, pk=pk)
    if obj.status != "Draft":
        messages.error(request, "Only Draft goods receipts can be posted.")
        return redirect("goodsreceipt_detail", pk=pk)

    with transaction.atomic():
        for line in obj.lines.select_related("item"):
            stock, _ = Stock.objects.get_or_create(
                item=line.item, warehouse=obj.warehouse, defaults={"quantity": 0}
            )
            stock.quantity += line.quantity
            stock.save()
            _record_stock_movement(
                line.item, obj.warehouse, line.quantity,
                "Purchase Receipt", request.user, stock.quantity,
                reference_document="GoodsReceipt", reference_number=obj.receipt_number,
            )
        obj.status = "Posted"
        obj.save()

    log_activity(
        request.user, "Post Goods Receipt", app_label="purchasing",
        model_name="GoodsReceipt", object_id=obj.pk, object_repr=obj.receipt_number,
        new_values={"status": "Posted"}, request=request,
    )
    messages.success(request, "Goods receipt posted. Inventory has been increased.")
    return redirect("goodsreceipt_detail", pk=pk)


@permission_required("purchasing.change_goodsreceipt", raise_exception=True)
def goodsreceipt_cancel(request, pk):
    obj = get_object_or_404(GoodsReceipt, pk=pk)
    if obj.status != "Draft":
        messages.error(request, "Only Draft goods receipts can be cancelled.")
        return redirect("goodsreceipt_detail", pk=pk)
    obj.status = "Cancelled"
    obj.save()
    log_activity(
        request.user, "Cancel Goods Receipt", app_label="purchasing",
        model_name="GoodsReceipt", object_id=obj.pk, object_repr=obj.receipt_number,
        new_values={"status": "Cancelled"}, request=request,
    )
    messages.success(request, "Goods receipt cancelled.")
    return redirect("goodsreceipt_detail", pk=pk)


# ===================================================================
# A/P Invoice (E)
# ===================================================================

@permission_required("purchasing.view_apinvoice", raise_exception=True)
def apinvoice_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    items = APInvoice.objects.select_related("supplier").order_by("-created_at")
    if query:
        items = items.filter(
            Q(invoice_number__icontains=query) | Q(supplier__name__icontains=query)
        )
    if status:
        items = items.filter(status=status)
    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = _list_context(
        "A/P Invoices",
        [
            {"label": "Invoice #", "key": "invoice_number", "link": "apinvoice_detail"},
            {"label": "Supplier", "key": "supplier"},
            {"label": "Date", "key": "invoice_date"},
            {"label": "Status", "key": "status"},
        ],
        "apinvoice_create",
        "apinvoice_detail",
        ["Draft", "Open", "Partial", "Paid", "Cancelled"],
    )
    context.update({"page_obj": page_obj, "query": query, "status": status})
    return render(request, "purchasing/doc_list.html", context)


@permission_required("purchasing.add_apinvoice", raise_exception=True)
def apinvoice_create(request):
    """Create an A/P Invoice, optionally from a Posted Goods Receipt (?receipt=<id>)."""
    receipt = _get_or_none(GoodsReceipt, request.GET.get("receipt"))
    initial = {}
    line_initial = []
    if receipt:
        initial = {"supplier": receipt.supplier, "goods_receipt": receipt}
        line_initial = [
            {
                "item": l.item_id,
                "quantity": l.quantity,
                "unit_price": l.unit_price,
                "discount_percent": l.discount_percent,
                "tax_percent": l.tax_percent,
            }
            for l in receipt.lines.all()
        ]

    if request.method == "POST":
        form = APInvoiceForm(request.POST)
        formset = APInvoiceLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.status = "Open"
            obj.save()
            formset.instance = obj
            formset.save()
            log_activity(
                request.user, "Create A/P Invoice", app_label="purchasing",
                model_name="APInvoice", object_id=obj.pk, object_repr=obj.invoice_number,
                new_values={"invoice_number": obj.invoice_number, "supplier": str(obj.supplier)},
                request=request,
            )
            messages.success(request, f"A/P invoice {obj.invoice_number} created.")
            return redirect("apinvoice_detail", pk=obj.pk)
    else:
        form = APInvoiceForm(initial=initial)
        formset = APInvoiceLineFormSet(initial=line_initial)
    return render(
        request, "purchasing/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Create A/P Invoice",
            "lines_title": "Invoice Lines",
            "cancel_url": "apinvoice_list",
        },
    )


@permission_required("purchasing.view_apinvoice", raise_exception=True)
def apinvoice_detail(request, pk):
    obj = get_object_or_404(
        APInvoice.objects.select_related("supplier", "order", "goods_receipt"), pk=pk
    )
    actions = []
    if obj.status in ("Draft", "Open"):
        actions.append(("Create Outgoing Payment", _action_url("outgoingpayment_create", query={"invoice": obj.pk}), ""))
        actions.append(("Cancel Invoice", _action_url("apinvoice_cancel", pk=obj.pk), "btn-danger"))
    return render(
        request, "purchasing/doc_detail.html",
        {
            "doc": obj,
            "doc_number": obj.invoice_number,
            "info_fields": [
                ("Supplier", obj.supplier.name),
                ("Goods Receipt", obj.goods_receipt.receipt_number if obj.goods_receipt else "-"),
                ("Date", obj.invoice_date),
                ("Due Date", obj.due_date or "-"),
                ("Status", obj.get_status_display()),
                ("Paid Amount", obj.paid_amount),
                ("Balance", obj.balance),
                ("Remarks", obj.remarks or "-"),
            ],
            "lines": obj.lines.select_related("item"),
            "lines_title": "Invoice Lines",
            "total": obj.total,
            "actions": actions,
            "list_url": "apinvoice_list",
        },
    )


@permission_required("purchasing.change_apinvoice", raise_exception=True)
def apinvoice_cancel(request, pk):
    obj = get_object_or_404(APInvoice, pk=pk)
    if obj.status not in ("Draft", "Open"):
        messages.error(request, "Only Draft or Open invoices can be cancelled.")
        return redirect("apinvoice_detail", pk=pk)
    obj.status = "Cancelled"
    obj.save()
    log_activity(
        request.user, "Cancel A/P Invoice", app_label="purchasing",
        model_name="APInvoice", object_id=obj.pk, object_repr=obj.invoice_number,
        new_values={"status": "Cancelled"}, request=request,
    )
    messages.success(request, "Invoice cancelled.")
    return redirect("apinvoice_detail", pk=pk)


# ===================================================================
# A/P Credit Memo (F)
# ===================================================================

@permission_required("purchasing.view_apcreditmemo", raise_exception=True)
def apcreditmemo_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    items = APCreditMemo.objects.select_related("supplier").order_by("-created_at")
    if query:
        items = items.filter(
            Q(credit_memo_number__icontains=query) | Q(supplier__name__icontains=query)
        )
    if status:
        items = items.filter(status=status)
    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = _list_context(
        "A/P Credit Memos",
        [
            {"label": "Memo #", "key": "credit_memo_number", "link": "apcreditmemo_detail"},
            {"label": "Supplier", "key": "supplier"},
            {"label": "Date", "key": "credit_date"},
            {"label": "Status", "key": "status"},
        ],
        "apcreditmemo_create",
        "apcreditmemo_detail",
        ["Draft", "Open", "Applied", "Cancelled"],
    )
    context.update({"page_obj": page_obj, "query": query, "status": status})
    return render(request, "purchasing/doc_list.html", context)


@permission_required("purchasing.add_apcreditmemo", raise_exception=True)
def apcreditmemo_create(request):
    """Create an A/P Credit Memo, optionally for an Open A/P Invoice (?invoice=<id>)."""
    invoice = _get_or_none(APInvoice, request.GET.get("invoice"))
    initial = {}
    line_initial = []
    if invoice:
        initial = {"supplier": invoice.supplier, "invoice": invoice}
        line_initial = [
            {
                "item": l.item_id,
                "quantity": l.quantity,
                "unit_price": l.unit_price,
                "discount_percent": l.discount_percent,
                "tax_percent": l.tax_percent,
            }
            for l in invoice.lines.all()
        ]

    if request.method == "POST":
        form = APCreditMemoForm(request.POST)
        formset = APCreditMemoLineFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.status = "Open"
            obj.save()
            formset.instance = obj
            formset.save()
            log_activity(
                request.user, "Create A/P Credit Memo", app_label="purchasing",
                model_name="APCreditMemo", object_id=obj.pk, object_repr=obj.credit_memo_number,
                new_values={"credit_memo_number": obj.credit_memo_number, "supplier": str(obj.supplier)},
                request=request,
            )
            messages.success(request, f"Credit memo {obj.credit_memo_number} created.")
            return redirect("apcreditmemo_detail", pk=obj.pk)
    else:
        form = APCreditMemoForm(initial=initial)
        formset = APCreditMemoLineFormSet(initial=line_initial)
    return render(
        request, "purchasing/doc_form.html",
        {
            "form": form,
            "formset": formset,
            "title": "Create A/P Credit Memo",
            "lines_title": "Credit Memo Lines",
            "cancel_url": "apcreditmemo_list",
        },
    )


@permission_required("purchasing.view_apcreditmemo", raise_exception=True)
def apcreditmemo_detail(request, pk):
    obj = get_object_or_404(
        APCreditMemo.objects.select_related("supplier", "invoice"), pk=pk
    )
    actions = []
    if obj.status == "Open":
        actions.append(("Apply Memo", _action_url("apcreditmemo_apply", pk=obj.pk), ""))
        actions.append(("Cancel Memo", _action_url("apcreditmemo_cancel", pk=obj.pk), "btn-danger"))
    return render(
        request, "purchasing/doc_detail.html",
        {
            "doc": obj,
            "doc_number": obj.credit_memo_number,
            "info_fields": [
                ("Supplier", obj.supplier.name),
                ("Invoice", obj.invoice.invoice_number if obj.invoice else "-"),
                ("Date", obj.credit_date),
                ("Status", obj.get_status_display()),
                ("Remarks", obj.remarks or "-"),
            ],
            "lines": obj.lines.select_related("item"),
            "lines_title": "Credit Memo Lines",
            "total": obj.total,
            "actions": actions,
            "list_url": "apcreditmemo_list",
        },
    )


@permission_required("purchasing.change_apcreditmemo", raise_exception=True)
def apcreditmemo_apply(request, pk):
    obj = get_object_or_404(APCreditMemo, pk=pk)
    if obj.status != "Open":
        messages.error(request, "Only Open credit memos can be applied.")
        return redirect("apcreditmemo_detail", pk=pk)
    obj.status = "Applied"
    obj.save()
    log_activity(
        request.user, "Apply A/P Credit Memo", app_label="purchasing",
        model_name="APCreditMemo", object_id=obj.pk, object_repr=obj.credit_memo_number,
        new_values={"status": "Applied"}, request=request,
    )
    messages.success(request, "Credit memo applied. Supplier payable reduced.")
    return redirect("apcreditmemo_detail", pk=pk)


@permission_required("purchasing.change_apcreditmemo", raise_exception=True)
def apcreditmemo_cancel(request, pk):
    obj = get_object_or_404(APCreditMemo, pk=pk)
    if obj.status not in ("Draft", "Open"):
        messages.error(request, "Only Draft or Open credit memos can be cancelled.")
        return redirect("apcreditmemo_detail", pk=pk)
    obj.status = "Cancelled"
    obj.save()
    log_activity(
        request.user, "Cancel A/P Credit Memo", app_label="purchasing",
        model_name="APCreditMemo", object_id=obj.pk, object_repr=obj.credit_memo_number,
        new_values={"status": "Cancelled"}, request=request,
    )
    messages.success(request, "Credit memo cancelled.")
    return redirect("apcreditmemo_detail", pk=pk)


# ===================================================================
# Outgoing Payment (G)
# ===================================================================

@permission_required("purchasing.view_outgoingpayment", raise_exception=True)
def outgoingpayment_list(request):
    query = request.GET.get("q", "")
    status = request.GET.get("status", "")
    items = OutgoingPayment.objects.select_related("supplier", "invoice").order_by("-created_at")
    if query:
        items = items.filter(
            Q(payment_number__icontains=query) | Q(supplier__name__icontains=query)
        )
    if status:
        items = items.filter(status=status)
    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = _list_context(
        "Outgoing Payments",
        [
            {"label": "Payment #", "key": "payment_number", "link": "outgoingpayment_detail"},
            {"label": "Supplier", "key": "supplier"},
            {"label": "Date", "key": "payment_date"},
            {"label": "Amount", "key": "amount"},
            {"label": "Status", "key": "status"},
        ],
        "outgoingpayment_create",
        "outgoingpayment_detail",
        ["Draft", "Completed", "Cancelled"],
    )
    context.update({"page_obj": page_obj, "query": query, "status": status})
    return render(request, "purchasing/doc_list.html", context)


@permission_required("purchasing.add_outgoingpayment", raise_exception=True)
def outgoingpayment_create(request):
    """Create an Outgoing Payment, optionally for an Open A/P Invoice (?invoice=<id>)."""
    invoice = _get_or_none(APInvoice, request.GET.get("invoice"))
    initial = {}
    if invoice:
        initial = {"supplier": invoice.supplier, "invoice": invoice, "amount": invoice.balance}

    if request.method == "POST":
        form = OutgoingPaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.created_by = request.user
            payment.status = "Draft"
            payment.save()
            log_activity(
                request.user, "Create Outgoing Payment", app_label="purchasing",
                model_name="OutgoingPayment", object_id=payment.pk, object_repr=payment.payment_number,
                new_values={"payment_number": payment.payment_number, "amount": str(payment.amount)},
                request=request,
            )
            messages.success(request, f"Payment {payment.payment_number} created (Draft).")
            return redirect("outgoingpayment_detail", pk=payment.pk)
    else:
        form = OutgoingPaymentForm(initial=initial)
    return render(
        request, "purchasing/outgoingpayment_form.html",
        {"form": form, "title": "Create Outgoing Payment"},
    )


@permission_required("purchasing.view_outgoingpayment", raise_exception=True)
def outgoingpayment_detail(request, pk):
    payment = get_object_or_404(
        OutgoingPayment.objects.select_related("supplier", "invoice"), pk=pk
    )
    actions = []
    if payment.status == "Draft":
        actions.append(("Complete Payment", _action_url("outgoingpayment_complete", pk=payment.pk), ""))
        actions.append(("Cancel Payment", _action_url("outgoingpayment_cancel", pk=payment.pk), "btn-danger"))
    return render(
        request, "purchasing/outgoingpayment_detail.html",
        {
            "payment": payment,
            "doc": payment,
            "doc_number": payment.payment_number,
            "info_fields": [
                ("Supplier", payment.supplier.name),
                ("Invoice", payment.invoice.invoice_number if payment.invoice else "-"),
                ("Date", payment.payment_date),
                ("Amount", payment.amount),
                ("Method", payment.payment_method),
                ("Reference", payment.reference or "-"),
                ("Status", payment.get_status_display()),
            ],
            "actions": actions,
            "list_url": "outgoingpayment_list",
        },
    )


@permission_required("purchasing.change_outgoingpayment", raise_exception=True)
def outgoingpayment_complete(request, pk):
    """Complete the payment and update the invoice balance."""
    payment = get_object_or_404(OutgoingPayment, pk=pk)
    if payment.status != "Draft":
        messages.error(request, "Only Draft payments can be completed.")
        return redirect("outgoingpayment_detail", pk=pk)

    with transaction.atomic():
        payment.status = "Completed"
        payment.save()
        if payment.invoice:
            invoice = payment.invoice
            balance = invoice.total - invoice.paid_amount
            invoice.status = "Paid" if balance <= 0 else "Partial"
            invoice.save(update_fields=["status"])

    log_activity(
        request.user, "Complete Outgoing Payment", app_label="purchasing",
        model_name="OutgoingPayment", object_id=payment.pk, object_repr=payment.payment_number,
        new_values={"status": "Completed", "amount": str(payment.amount)}, request=request,
    )
    messages.success(request, "Payment completed. Supplier payable updated.")
    return redirect("outgoingpayment_detail", pk=pk)


@permission_required("purchasing.change_outgoingpayment", raise_exception=True)
def outgoingpayment_cancel(request, pk):
    payment = get_object_or_404(OutgoingPayment, pk=pk)
    if payment.status != "Draft":
        messages.error(request, "Only Draft payments can be cancelled.")
        return redirect("outgoingpayment_detail", pk=pk)
    payment.status = "Cancelled"
    payment.save()
    log_activity(
        request.user, "Cancel Outgoing Payment", app_label="purchasing",
        model_name="OutgoingPayment", object_id=payment.pk, object_repr=payment.payment_number,
        new_values={"status": "Cancelled"}, request=request,
    )
    messages.success(request, "Payment cancelled.")
    return redirect("outgoingpayment_detail", pk=pk)
