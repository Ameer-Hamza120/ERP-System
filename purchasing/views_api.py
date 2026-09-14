import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from audit.log import log_activity

from .models import (
    Supplier, PurchaseRequest, PurchaseQuotation, PurchaseOrder, GoodsReceipt,
    APInvoice, APCreditMemo, OutgoingPayment,
)
from .forms import SupplierForm


@require_http_methods(["GET", "POST"])
@login_required
def api_suppliers(request):
    if request.method == "GET":
        if not request.user.has_perm("purchasing.view_supplier"):
            return JsonResponse({"error": "Permission denied"}, status=403)
        suppliers = Supplier.objects.all()
        data = [
            {
                "id": s.id,
                "supplier_code": s.supplier_code,
                "name": s.name,
                "phone": s.phone,
                "email": s.email,
                "city": s.city,
                "is_active": s.is_active,
                "payable": float(s.payable),
            }
            for s in suppliers
        ]
        return JsonResponse(data, safe=False)

    elif request.method == "POST":
        if not request.user.has_perm("purchasing.add_supplier"):
            return JsonResponse({"error": "Permission denied"}, status=403)
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        form = SupplierForm(data)
        if form.is_valid():
            supplier = form.save()
            log_activity(
                request.user, "Create Supplier", app_label="purchasing",
                model_name="Supplier", object_id=supplier.pk, object_repr=supplier.name,
                new_values={"supplier_code": supplier.supplier_code, "name": supplier.name},
                request=request,
            )
            return JsonResponse(
                {"id": supplier.id, "supplier_code": supplier.supplier_code}, status=201
            )
        return JsonResponse({"errors": form.errors}, status=400)


@require_http_methods(["GET"])
@login_required
def api_supplier_detail(request, pk):
    try:
        supplier = Supplier.objects.get(pk=pk)
    except Supplier.DoesNotExist:
        return JsonResponse({"error": "Supplier not found"}, status=404)
    if not request.user.has_perm("purchasing.view_supplier"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    data = {
        "id": supplier.id,
        "supplier_code": supplier.supplier_code,
        "name": supplier.name,
        "phone": supplier.phone,
        "email": supplier.email,
        "city": supplier.city,
        "country": supplier.country,
        "payable": float(supplier.payable),
    }
    return JsonResponse(data)


@require_http_methods(["GET"])
@login_required
def api_purchase_requests(request):
    if not request.user.has_perm("purchasing.view_purchaserequest"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    items = PurchaseRequest.objects.values(
        "id", "request_number", "requested_by_name", "department", "request_date", "status"
    )
    return JsonResponse(list(items), safe=False)


@require_http_methods(["GET"])
@login_required
def api_purchase_quotations(request):
    if not request.user.has_perm("purchasing.view_purchasequotation"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    items = PurchaseQuotation.objects.select_related("supplier").values(
        "id", "quotation_number", "supplier__name", "quotation_date", "status"
    )
    return JsonResponse(list(items), safe=False)


@require_http_methods(["GET"])
@login_required
def api_purchase_orders(request):
    if not request.user.has_perm("purchasing.view_purchaseorder"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    items = PurchaseOrder.objects.select_related("supplier").values(
        "id", "order_number", "supplier__name", "order_date", "status"
    )
    return JsonResponse(list(items), safe=False)


@require_http_methods(["GET"])
@login_required
def api_goods_receipts(request):
    if not request.user.has_perm("purchasing.view_goodsreceipt"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    items = GoodsReceipt.objects.select_related("supplier", "warehouse").values(
        "id", "receipt_number", "supplier__name", "warehouse__name", "receipt_date", "status"
    )
    return JsonResponse(list(items), safe=False)


@require_http_methods(["GET"])
@login_required
def api_ap_invoices(request):
    if not request.user.has_perm("purchasing.view_apinvoice"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    items = APInvoice.objects.select_related("supplier").values(
        "id", "invoice_number", "supplier__name", "invoice_date", "status"
    )
    return JsonResponse(list(items), safe=False)


@require_http_methods(["GET"])
@login_required
def api_ap_credit_memos(request):
    if not request.user.has_perm("purchasing.view_apcreditmemo"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    items = APCreditMemo.objects.select_related("supplier").values(
        "id", "credit_memo_number", "supplier__name", "credit_date", "status"
    )
    return JsonResponse(list(items), safe=False)


@require_http_methods(["GET"])
@login_required
def api_outgoing_payments(request):
    if not request.user.has_perm("purchasing.view_outgoingpayment"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    items = OutgoingPayment.objects.select_related("supplier").values(
        "id", "payment_number", "supplier__name", "payment_date", "amount", "status"
    )
    return JsonResponse(list(items), safe=False)
