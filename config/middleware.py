from django.conf import settings


class NoCacheHTMLMiddleware:
    """Prevent browser caching of HTML during development only."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.DEBUG and response.get("Content-Type", "").startswith("text/html"):
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
        return response
