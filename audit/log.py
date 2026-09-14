from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .models import AuditLog


def log_activity(
    user,
    action,
    app_label="",
    model_name="",
    object_id="",
    object_repr="",
    old_values=None,
    new_values=None,
    request=None,
):
    ip_address = None
    user_agent = ""
    if request:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]

    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        username=user.username if user and user.is_authenticated else "Anonymous",
        action=action,
        app_label=app_label,
        model_name=model_name,
        object_id=str(object_id) if object_id else "",
        object_repr=object_repr[:255] if object_repr else "",
        old_values=old_values or {},
        new_values=new_values or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    log_activity(user, "Login", request=request)


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    log_activity(user, "Logout", request=request)