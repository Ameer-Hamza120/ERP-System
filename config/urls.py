from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("inventory/", include("inventory.urls")),
    path("sales/", include("sales.urls")),
    path("purchasing/", include("purchasing.urls")),
    path("reports/", include("reports.urls")),
    path("audit/", include("audit.urls")),
    # REST API
    path("api/", include("accounts.api_urls")),
    path("api/", include("inventory.api_urls")),
    path("api/", include("sales.api_urls")),
    path("api/", include("purchasing.api_urls")),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)