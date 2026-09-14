from decimal import Decimal
from urllib.parse import urlencode

from django.db.models.fields.files import FieldFile
from django.urls import reverse


def model_values(instance):
    """JSON-serializable snapshot of a model instance, for audit logging."""
    values = {}
    for field in instance._meta.fields:
        value = getattr(instance, field.name)
        if isinstance(value, FieldFile):
            value = value.name
        elif isinstance(value, Decimal):
            value = str(value)
        elif hasattr(value, "isoformat"):
            value = value.isoformat()
        elif hasattr(value, "pk"):
            value = value.pk
        values[field.name] = value
    return values


def get_or_none(model, pk):
    return model.objects.filter(pk=pk).first() if pk else None


def action_url(name, pk=None, query=None):
    url = reverse(name, args=[pk]) if pk is not None else reverse(name)
    return f"{url}?{urlencode(query)}" if query else url


def list_context(title, columns, create_url, detail_url, statuses):
    return {
        "title": title,
        "columns": columns,
        "create_url": create_url,
        "detail_url": detail_url,
        "statuses": statuses,
    }
