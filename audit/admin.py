from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "username",
        "action",
        "app_label",
        "model_name",
        "object_repr",
    )
    list_filter = ("action", "app_label", "model_name")
    search_fields = ("username", "action", "object_repr", "object_id")
    readonly_fields = (
        "user",
        "username",
        "action",
        "app_label",
        "model_name",
        "object_id",
        "object_repr",
        "old_values",
        "new_values",
        "ip_address",
        "user_agent",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False