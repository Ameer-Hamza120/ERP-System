from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import timedelta

from audit.log import log_activity

from inventory.models import Item, ItemGroup, Warehouse, Stock, StockTransfer

from sales.models import Customer, SalesQuotation, SalesOrder, ARInvoice
from purchasing.models import Supplier, PurchaseRequest, PurchaseOrder

from .forms import UserCreateForm, UserUpdateForm, RoleForm, CompanySettingsForm, DocumentSequenceForm
from .models import CompanySettings, DocumentSequence
from common.utils import model_values as _model_values


# ---------------- Login (with brute-force protection) ----------------

class ThrottledLoginView(LoginView):
    """Login view that locks an account after repeated failed attempts."""

    template_name = "accounts/login.html"

    def _get_key(self, username, ip):
        return f"login_fail_{username.strip().lower()}_{ip}"

    def _lockout_left(self, username, ip):
        attempts = cache.get(self._get_key(username, ip), 0)
        if attempts >= settings.LOGIN_MAX_ATTEMPTS:
            return settings.LOGIN_LOCKOUT_MINUTES
        return 0

    def dispatch(self, request, *args, **kwargs):
        ip = request.META.get("REMOTE_ADDR", "")
        username = request.POST.get("username", "")
        lockout = self._lockout_left(username, ip)
        if lockout:
            messages.error(
                request,
                f"Too many failed attempts. Try again in {lockout} minute(s).",
            )
            return render(
                request,
                "accounts/login.html",
                {"form": self.get_form(), "locked_out": True},
            )
        return super().dispatch(request, *args, **kwargs)

    def form_invalid(self, form):
        ip = self.request.META.get("REMOTE_ADDR", "")
        username = self.request.POST.get("username", "")
        key = self._get_key(username, ip)
        attempts = cache.get(key, 0) + 1
        cache.set(key, attempts, settings.LOGIN_LOCKOUT_MINUTES * 60)
        if attempts >= settings.LOGIN_MAX_ATTEMPTS:
            messages.error(
                self.request,
                "Too many failed attempts. Account temporarily locked.",
            )
        return super().form_invalid(form)

    def form_valid(self, form):
        ip = self.request.META.get("REMOTE_ADDR", "")
        username = self.request.POST.get("username", "")
        remember_me = self.request.POST.get("remember_me") == "on"
        cache.delete(self._get_key(username, ip))

        if remember_me:
            self.request.session.set_expiry(60 * 60 * 24 * 30)
        else:
            self.request.session.set_expiry(0)

        return super().form_valid(form)


# ---------------- Dashboard ----------------

@login_required
def dashboard(request):
    """Main dashboard after login. Widgets respect the user's permissions."""
    user = request.user
    context = {}

    if user.has_perm("auth.view_user"):
        context["total_users"] = User.objects.count()

    if user.has_perm("inventory.view_item"):
        context["total_items"] = Item.objects.count()

    if user.has_perm("inventory.view_itemgroup"):
        context["total_item_groups"] = ItemGroup.objects.count()

    if user.has_perm("inventory.view_warehouse"):
        context["total_warehouses"] = Warehouse.objects.count()

    if user.has_perm("inventory.view_stock"):
        context["total_stock"] = (
            Stock.objects.aggregate(total=Sum("quantity"))["total"] or 0
        )

    if user.has_perm("inventory.view_stock"):
        context["low_stock_items"] = (
            Item.objects.annotate(total_stock=Sum("stock_records__quantity"))
            .filter(total_stock__lte=F("minimum_stock_level"))
            .order_by("item_code")[:10]
        )

    if user.has_perm("inventory.view_stocktransfer"):
        context["recent_transfers"] = StockTransfer.objects.select_related(
            "item", "from_warehouse", "to_warehouse"
        ).order_by("-created_at")[:5]

    if user.has_perm("inventory.view_stocktransfer"):
        context["pending_approvals"] = (
            StockTransfer.objects.filter(status="Pending").count()
        )

    if user.has_perm("sales.view_customer"):
        context["total_customers"] = Customer.objects.count()

    if user.has_perm("sales.view_arinvoice"):
        context["open_ar_invoices"] = (
            ARInvoice.objects.exclude(status__in=["Paid", "Cancelled"]).count()
        )

    if user.has_perm("sales.view_salesorder"):
        context["open_sales_orders"] = (
            SalesOrder.objects.exclude(status__in=["Completed", "Cancelled"]).count()
        )

    if user.has_perm("purchasing.view_supplier"):
        context["total_suppliers"] = Supplier.objects.count()

    if user.has_perm("purchasing.view_purchaseorder"):
        context["open_purchase_orders"] = (
            PurchaseOrder.objects.exclude(status__in=["Completed", "Cancelled"]).count()
        )

    return render(request, "accounts/dashboard.html", context)


# ---------------- User Management ----------------

@permission_required("auth.view_user", raise_exception=True)
def user_list(request):
    """List all users with search."""
    query = request.GET.get("q", "")
    users = User.objects.prefetch_related("groups").order_by("username")

    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )

    paginator = Paginator(users, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "accounts/user_list.html",
        {"page_obj": page_obj, "query": query},
    )


@permission_required("auth.add_user", raise_exception=True)
def user_create(request):
    """Create a new user."""
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_activity(
                request.user,
                "Create User",
                app_label="auth",
                model_name="User",
                object_id=user.pk,
                object_repr=user.username,
                new_values={
                    "username": user.username,
                    "email": user.email,
                    "group": form.cleaned_data["group"].name if form.cleaned_data.get("group") else "",
                },
                request=request,
            )
            messages.success(request, "User added successfully.")
            return redirect("user_list")
    else:
        form = UserCreateForm()
    return render(request, "accounts/user_form.html", {"form": form, "title": "Add User"})


@permission_required("auth.change_user", raise_exception=True)
def user_update(request, pk):
    """Edit an existing user."""
    user = get_object_or_404(User, pk=pk)
    old_values = _model_values(user)
    if request.method == "POST":
        form = UserUpdateForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            log_activity(
                request.user,
                "Update User",
                app_label="auth",
                model_name="User",
                object_id=user.pk,
                object_repr=user.username,
                old_values=old_values,
                new_values=_model_values(user),
                request=request,
            )
            messages.success(request, "User updated successfully.")
            return redirect("user_list")
    else:
        form = UserUpdateForm(instance=user)
    return render(
        request,
        "accounts/user_form.html",
        {"form": form, "title": f"Edit User: {user.username}"},
    )


@permission_required("auth.delete_user", raise_exception=True)
def user_delete(request, pk):
    """Delete a user."""
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        log_activity(
            request.user,
            "Delete User",
            app_label="auth",
            model_name="User",
            object_id=user.pk,
            object_repr=user.username,
            request=request,
        )
        user.delete()
        messages.success(request, "User deleted successfully.")
        return redirect("user_list")
    return render(request, "accounts/user_confirm_delete.html", {"user": user})


@permission_required("auth.change_user", raise_exception=True)
def user_reset_password(request, pk):
    """Reset a user's password."""
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            log_activity(
                request.user,
                "Reset Password",
                app_label="auth",
                model_name="User",
                object_id=user.pk,
                object_repr=user.username,
                request=request,
            )
            messages.success(request, f"Password for {user.username} reset successfully.")
            return redirect("user_list")
    else:
        form = SetPasswordForm(user)
    return render(
        request,
        "accounts/user_password_reset.html",
        {"form": form, "user": user},
    )


# ---------------- Role Management ----------------

@permission_required("auth.view_group", raise_exception=True)
def role_list(request):
    """List all roles (groups)."""
    roles = Group.objects.prefetch_related("permissions").order_by("name")
    return render(request, "accounts/role_list.html", {"roles": roles})


@permission_required("auth.add_group", raise_exception=True)
def role_create(request):
    """Create a new role."""
    if request.method == "POST":
        form = RoleForm(request.POST)
        if form.is_valid():
            role = form.save()
            log_activity(
                request.user,
                "Create Role",
                app_label="auth",
                model_name="Group",
                object_id=role.pk,
                object_repr=role.name,
                new_values={"permissions": [p.codename for p in role.permissions.all()]},
                request=request,
            )
            messages.success(request, "Role added successfully.")
            return redirect("role_list")
    else:
        form = RoleForm()
    return render(request, "accounts/role_form.html", {"form": form, "title": "Add Role"})


@permission_required("auth.change_group", raise_exception=True)
def role_update(request, pk):
    """Edit a role and its permissions."""
    role = get_object_or_404(Group, pk=pk)
    old_perms = [p.codename for p in role.permissions.all()]
    if request.method == "POST":
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            role = form.save()
            log_activity(
                request.user,
                "Update Role",
                app_label="auth",
                model_name="Group",
                object_id=role.pk,
                object_repr=role.name,
                old_values={"permissions": old_perms},
                new_values={"permissions": [p.codename for p in role.permissions.all()]},
                request=request,
            )
            messages.success(request, "Role updated successfully.")
            return redirect("role_list")
    else:
        form = RoleForm(instance=role)
    return render(
        request,
        "accounts/role_form.html",
        {"form": form, "title": f"Edit Role: {role.name}"},
    )


@permission_required("auth.delete_group", raise_exception=True)
def role_delete(request, pk):
    """Delete a role."""
    role = get_object_or_404(Group, pk=pk)
    if request.method == "POST":
        log_activity(
            request.user,
            "Delete Role",
            app_label="auth",
            model_name="Group",
            object_id=role.pk,
            object_repr=role.name,
            request=request,
        )
        role.delete()
        messages.success(request, "Role deleted successfully.")
        return redirect("role_list")
    return render(request, "accounts/role_confirm_delete.html", {"role": role})


# ---------------- Company Settings ----------------

@permission_required("accounts.change_companysettings", raise_exception=True)
def company_settings(request):
    """Edit company settings (singleton)."""
    obj = CompanySettings.objects.first()
    if not obj:
        obj = CompanySettings.objects.create(company_name="My Company")

    old_values = _model_values(obj)
    if request.method == "POST":
        form = CompanySettingsForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            log_activity(
                request.user,
                "Update Company Settings",
                app_label="accounts",
                model_name="CompanySettings",
                object_id=obj.pk,
                object_repr=obj.company_name,
                old_values=old_values,
                new_values=_model_values(obj),
                request=request,
            )
            messages.success(request, "Company settings updated.")
            return redirect("company_settings")
    else:
        form = CompanySettingsForm(instance=obj)

    return render(request, "accounts/company_settings.html", {"form": form})


# ---------------- Document Sequences ----------------

@permission_required("accounts.view_documentsequence", raise_exception=True)
def document_sequence_list(request):
    sequences = DocumentSequence.objects.all().order_by("document_type")
    return render(
        request,
        "accounts/document_sequence_list.html",
        {"sequences": sequences},
    )


@permission_required("accounts.change_documentsequence", raise_exception=True)
def document_sequence_update(request, pk):
    seq = get_object_or_404(DocumentSequence, pk=pk)
    if request.method == "POST":
        form = DocumentSequenceForm(request.POST, instance=seq)
        if form.is_valid():
            form.save()
            log_activity(
                request.user,
                "Update Document Sequence",
                app_label="accounts",
                model_name="DocumentSequence",
                object_id=seq.pk,
                object_repr=seq.document_type,
                request=request,
            )
            messages.success(request, "Document sequence updated successfully.")
            return redirect("document_sequence_list")
    else:
        form = DocumentSequenceForm(instance=seq)
    return render(
        request,
        "accounts/document_sequence_form.html",
        {"form": form, "title": f"Edit Sequence: {seq.document_type}"},
    )