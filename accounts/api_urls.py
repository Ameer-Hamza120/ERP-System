from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views_api

router = DefaultRouter()
router.register(r"users", views_api.UserViewSet, basename="api_user")
router.register(r"groups", views_api.GroupViewSet, basename="api_group")
router.register(r"permissions", views_api.PermissionViewSet, basename="api_permission")
router.register(
    r"document-sequences",
    views_api.DocumentSequenceViewSet,
    basename="api_document_sequence",
)

urlpatterns = [
    path("auth/login/", views_api.api_login, name="api_login"),
    path("auth/logout/", views_api.api_logout, name="api_logout"),
    path("auth/me/", views_api.api_me, name="api_me"),
    path("company-settings/", views_api.api_company_settings, name="api_company_settings"),
]

urlpatterns += router.urls