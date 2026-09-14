from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import AuditLog
from .log import log_activity


class AuditLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin", password="adminpass123"
        )
        self.client.login(username="admin", password="adminpass123")

    def test_log_activity_creates_entry(self):
        AuditLog.objects.all().delete()
        log_activity(
            self.user,
            "Test Action",
            app_label="test",
            model_name="TestModel",
            object_id="1",
            object_repr="Test Object",
        )
        self.assertEqual(AuditLog.objects.count(), 1)
        entry = AuditLog.objects.first()
        self.assertEqual(entry.username, "admin")
        self.assertEqual(entry.action, "Test Action")

    def test_log_activity_without_user(self):
        AuditLog.objects.all().delete()
        log_activity(None, "Anonymous Action", app_label="test")
        self.assertEqual(AuditLog.objects.count(), 1)
        entry = AuditLog.objects.first()
        self.assertEqual(entry.username, "Anonymous")

    def test_login_creates_audit_log(self):
        self.client.logout()
        AuditLog.objects.all().delete()
        self.client.login(username="admin", password="adminpass123")
        self.assertTrue(AuditLog.objects.filter(action="Login").exists())

    def test_audit_log_list_permission(self):
        response = self.client.get(reverse("auditlog_list"))
        self.assertEqual(response.status_code, 200)

    def test_audit_log_detail(self):
        log_activity(self.user, "Detail Test", object_repr="Detail Object")
        entry = AuditLog.objects.first()
        response = self.client.get(reverse("auditlog_detail", args=[entry.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Detail Object")