from inventory.models import StockTransfer


def global_context(request):
    """Context available on every page: pending approvals, company settings."""
    context = {}
    if request.user.is_authenticated:
        if request.user.has_perm("inventory.view_stocktransfer"):
            context["pending_approval_count"] = StockTransfer.objects.filter(
                status="Pending"
            ).count()
        else:
            context["pending_approval_count"] = 0

    from .models import CompanySettings

    context["company"] = CompanySettings.objects.first()
    return context