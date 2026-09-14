import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from audit.log import log_activity

from .models import (
    Customer, SalesQuotation, SalesOrder, Delivery, ReturnRequest, SalesReturn,
    ARInvoice, ARCreditMemo, IncomingPayment,
)
from .forms import CustomerForm


@require_http_methods(["GET", "POST"])
@login_required
def api_customers(request):
    if request.method == "GET":
        if not request.user.has_perm("sales.view_customer"):
            return JsonResponse({"error": "Permission denied"}, status=403)
        customers = Customer.objects.all()
        data = [
            {
                "id": c.id,
                "customer_code": c.customer_code,
                "name": c.name,
                "phone": c.phone,
                "email": c.email,
                "city": c.city,
                "is_active": c.is_active,
                "receivable": float(c.receivable),
            }
            for c in customers
        ]
        return JsonResponse(data, safe=False)

    elif request.method == "POST":
        if not request.user.has_perm("sales.add_customer"):
            return JsonResponse({"error": "Permission denied"}, status=403)
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        form = CustomerForm(data)
        if form.is_valid():
            customer = form.save()
            log_activity(
                request.user, "Create Customer", app_label="sales",
                model_name="Customer", object_id=customer.pk, object_repr=customer.name,
                new_values={"customer_code": customer.customer_code, "name": customer.name},
                request=request,
            )
            return JsonResponse(
                {"id": customer.id, "customer_code": customer.customer_code}, status=201
            )
        return JsonResponse({"errors": form.errors}, status=400)


@require_http_methods(["GET"])
@login_required
def api_customer_detail(request, pk):
    try:
        customer = Customer.objects.get(pk=pk)
    except Customer.DoesNotExist:
        return JsonResponse({"error": "Customer not found"}, status=404)
    if not request.user.has_perm("sales.view_customer"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    data = {
        "id": customer.id,
        "customer_code": customer.customer_code,
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
        "city": customer.city,
        "country": customer.country,
        "receivable": float(customer.receivable),
    }
    return JsonResponse(data)


@require_http_methods(["GET"])
@login_required
def api_sales_quotations(request):
    if not request.user.has_perm("sales.view_salesquotation"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    quotes = SalesQuotation.objects.select_related("customer").values(
        "id", "quotation_number", "customer__name", "quotation_date", "status"
    )
    return JsonResponse(list(quotes), safe=False)


@require_http_methods(["GET"])
@login_required
def api_sales_orders(request):
    if not request.user.has_perm("sales.view_salesorder"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    orders = SalesOrder.objects.select_related("customer").values(
        "id", "order_number", "customer__name", "order_date", "status"
    )
    return JsonResponse(list(orders), safe=False)


@require_http_methods(["GET"])
@login_required
def api_deliveries(request):
    if not request.user.has_perm("sales.view_delivery"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    deliveries = Delivery.objects.select_related("customer", "warehouse").values(
        "id", "delivery_number", "customer__name", "warehouse__name", "delivery_date", "status"
    )
    return JsonResponse(list(deliveries), safe=False)


@require_http_methods(["GET"])
@login_required
def api_ar_invoices(request):
    if not request.user.has_perm("sales.view_arinvoice"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    invoices = ARInvoice.objects.select_related("customer").values(
        "id", "invoice_number", "customer__name", "invoice_date", "status"
    )
    return JsonResponse(list(invoices), safe=False)


@require_http_methods(["GET"])
@login_required
def api_incoming_payments(request):
    if not request.user.has_perm("sales.view_incomingpayment"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    payments = IncomingPayment.objects.select_related("customer").values(
        "id", "payment_number", "customer__name", "payment_date", "amount", "status"
    )
    return JsonResponse(list(payments), safe=False)


@require_http_methods(["GET"])
@login_required
def api_return_requests(request):
    if not request.user.has_perm("sales.view_returnrequest"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    items = ReturnRequest.objects.select_related("customer").values(
        "id", "request_number", "customer__name", "request_date", "status"
    )
    return JsonResponse(list(items), safe=False)


@require_http_methods(["GET"])
@login_required
def api_sales_returns(request):
    if not request.user.has_perm("sales.view_salesreturn"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    items = SalesReturn.objects.select_related("customer", "warehouse").values(
        "id", "return_number", "customer__name", "warehouse__name", "return_date", "status"
    )
    return JsonResponse(list(items), safe=False)


@require_http_methods(["GET"])
@login_required
def api_ar_credit_memos(request):
    if not request.user.has_perm("sales.view_arcreditmemo"):
        return JsonResponse({"error": "Permission denied"}, status=403)
    memos = ARCreditMemo.objects.select_related("customer").values(
        "id", "credit_memo_number", "customer__name", "credit_date", "status"
    )
    return JsonResponse(list(memos), safe=False)
