from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404

from .models import AuditLog


@login_required
@permission_required("audit.can_view_auditlog", raise_exception=True)
def auditlog_list(request):
    query = request.GET.get("q", "")
    user_id = request.GET.get("user", "")
    action = request.GET.get("action", "")

    logs = AuditLog.objects.select_related("user").order_by("-created_at")

    if query:
        logs = logs.filter(
            Q(username__icontains=query)
            | Q(action__icontains=query)
            | Q(object_repr__icontains=query)
            | Q(model_name__icontains=query)
        )
    if user_id:
        logs = logs.filter(user_id=user_id)
    if action:
        logs = logs.filter(action__iexact=action)

    actions = (
        AuditLog.objects.values_list("action", flat=True)
        .distinct()
        .order_by("action")
    )

    paginator = Paginator(logs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "audit/auditlog_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "user_id": user_id,
            "action": action,
            "actions": actions,
        },
    )


@login_required
@permission_required("audit.can_view_auditlog", raise_exception=True)
def auditlog_detail(request, pk):
    log = get_object_or_404(AuditLog.objects.select_related("user"), pk=pk)
    return render(request, "audit/auditlog_detail.html", {"log": log})