from django import template

register = template.Library()


@register.filter
def attr(obj, name):
    """Resolve an attribute or property by name on the object."""
    try:
        value = getattr(obj, name)
        if callable(value):
            value = value()
        return value
    except (AttributeError, TypeError, ValueError):
        return "-"
