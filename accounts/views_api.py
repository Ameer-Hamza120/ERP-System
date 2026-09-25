from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group, Permission
from rest_framework import status, viewsets, mixins
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models import CompanySettings, DocumentSequence
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    GroupSerializer,
    PermissionSerializer,
    CompanySettingsSerializer,
    DocumentSequenceSerializer,
    MeSerializer,
)


class LoginThrottle(AnonRateThrottle):
    scope = "login"


@api_view(["POST"])
@permission_classes([AllowAny])
def api_login(request):
    """Authenticate a user and establish a session."""
    throttle = LoginThrottle()
    if not throttle.allow_request(request, None):
        return Response(
            {"detail": "Too many login attempts. Try again later."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {"detail": "Invalid username or password."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not user.is_active:
        return Response(
            {"detail": "This account is inactive."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    login(request, user)
    return Response(MeSerializer(user).data)


@api_view(["POST"])
def api_logout(request):
    logout(request)
    return Response({"detail": "Logged out."})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_me(request):
    return Response(MeSerializer(request.user).data)


class PermissionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = PermissionSerializer
    pagination_class = None

    def list(self, request, *args, **kwargs):
        if not request.user.has_perm("auth.view_permission"):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs = Permission.objects.select_related("content_type").order_by(
            "content_type__app_label", "codename"
        )
        app = self.request.query_params.get("app")
        if app:
            qs = qs.filter(content_type__app_label=app)
        return qs


class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer
    pagination_class = None

    def get_queryset(self):
        return Group.objects.prefetch_related("permissions").order_by("name")

    def list(self, request, *args, **kwargs):
        if not request.user.has_perm("auth.view_group"):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not request.user.has_perm("auth.add_group"):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if not request.user.has_perm("auth.change_group"):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.has_perm("auth.delete_group"):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class UserViewSet(viewsets.ModelViewSet):
    pagination_class = None

    def get_serializer_class(self):
        if self.action in ("create",):
            return UserCreateSerializer
        return UserSerializer

    def get_queryset(self):
        return User.objects.prefetch_related("groups").order_by("username")

    def list(self, request, *args, **kwargs):
        if not request.user.has_perm("auth.view_user"):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        if not request.user.has_perm("auth.add_user"):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if not request.user.has_perm("auth.change_user"):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.has_perm("auth.delete_user"):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def api_company_settings(request):
    if not request.user.has_perm("accounts.change_companysettings"):
        return Response(
            {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
        )
    obj = CompanySettings.objects.first()
    if not obj:
        obj = CompanySettings.objects.create(company_name="My Company")
    if request.method == "GET":
        return Response(CompanySettingsSerializer(obj).data)
    serializer = CompanySettingsSerializer(obj, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


class DocumentSequenceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = DocumentSequenceSerializer
    pagination_class = None

    def get_queryset(self):
        return DocumentSequence.objects.all().order_by("document_type")

    def list(self, request, *args, **kwargs):
        if not request.user.has_perm("accounts.change_documentsequence"):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )
        return super().list(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not request.user.has_perm("accounts.change_documentsequence"):
            return Response(
                {"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)


class HealthCheckView(viewsets.ViewSet):
    """Health check endpoint for monitoring and load balancers."""

    permission_classes = [AllowAny]

    def list(self, request):
        from django.db import connection
        from django.core.cache import cache
        import redis

        health_status = {
            "status": "healthy",
            "database": "ok",
            "cache": "ok",
        }

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            health_status["database"] = f"error: {str(e)}"
            health_status["status"] = "unhealthy"

        try:
            cache.set("health_check", "ok", 10)
            cache.get("health_check")
        except Exception as e:
            health_status["cache"] = f"error: {str(e)}"
            health_status["status"] = "degraded"

        http_status = (
            status.HTTP_200_OK
            if health_status["status"] == "healthy"
            else (
                status.HTTP_503_SERVICE_UNAVAILABLE
                if health_status["status"] == "unhealthy"
                else status.HTTP_200_OK
            )
        )

        return Response(health_status, status=http_status)