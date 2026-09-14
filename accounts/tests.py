from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.urls import reverse

from .models import CompanySettings, DocumentSequence
from audit.models import AuditLog


class UserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="testuser", password="testpass123"
        )
        self.client.login(username="testuser", password="testpass123")

    def test_dashboard_view(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")
        self.assertNotContains(response, "Recent Activity")

    def test_login_page_has_remember_me_option(self):
        self.client.logout()
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Remember me")

    def test_user_list_view(self):
        response = self.client.get(reverse("user_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "testuser")

    def test_login_page(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_user_create_records_audit(self):
        from django.contrib.auth.models import Group

        AuditLog.objects.all().delete()
        group = Group.objects.create(name="Tester Role")
        response = self.client.post(
            reverse("user_create"),
            {
                "username": "newuser",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
                "first_name": "New",
                "last_name": "User",
                "email": "new@example.com",
                "is_active": True,
                "group": group.id,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AuditLog.objects.filter(action="Create User").exists())
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_company_settings_update(self):
        response = self.client.post(
            reverse("company_settings"),
            {
                "company_name": "Test Corp",
                "address": "123 Main St",
                "city": "Muscat",
                "country": "Oman",
                "phone": "12345678",
                "email": "info@testcorp.com",
                "website": "https://testcorp.com",
                "tax_id": "VAT-001",
                "currency": "OMR",
                "date_format": "Y-m-d",
                "timezone": "UTC",
                "invoice_terms": "Net 30",
                "default_payment_terms": "Net 30",
                "fiscal_year_start": "",
                "fiscal_year_end": "",
                "default_warehouse": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        settings = CompanySettings.objects.first()
        self.assertEqual(settings.tax_id, "VAT-001")
        self.assertEqual(settings.city, "Muscat")
        self.assertTrue(AuditLog.objects.filter(action="Update Company Settings").exists())


class LoginThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="victim", password="correct-password-123"
        )

    @override_settings(LOGIN_MAX_ATTEMPTS=3, LOGIN_LOCKOUT_MINUTES=15)
    def test_login_locks_after_max_attempts(self):
        for _ in range(3):
            response = self.client.post(
                reverse("login"),
                {"username": "victim", "password": "wrong-password"},
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("login"),
            {"username": "victim", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Too many failed attempts")

    @override_settings(LOGIN_MAX_ATTEMPTS=3, LOGIN_LOCKOUT_MINUTES=15)
    def test_successful_login_clears_failures(self):
        for _ in range(2):
            self.client.post(
                reverse("login"),
                {"username": "victim", "password": "wrong-password"},
            )
        response = self.client.post(
            reverse("login"),
            {"username": "victim", "password": "correct-password-123"},
        )
        self.assertEqual(response.status_code, 302)

    def test_successful_login(self):
        response = self.client.post(
            reverse("login"),
            {"username": "victim", "password": "correct-password-123"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(AuditLog.objects.filter(action="Login").exists())


class DocumentSequenceTests(TestCase):
    def test_get_next_generates_sequential_unique_numbers(self):
        seq = DocumentSequence.objects.create(
            document_type="SO", prefix="SO", include_year=True, next_number=1, padding=6
        )
        first = DocumentSequence.get_next("SO")
        second = DocumentSequence.get_next("SO")
        self.assertRegex(first, r"^SO-\d{4}-000001$")
        self.assertRegex(second, r"^SO-\d{4}-000002$")
        self.assertNotEqual(first, second)
        seq.refresh_from_db()
        self.assertEqual(seq.next_number, 3)
        self.assertEqual(seq.last_number, second)

    def test_get_next_without_year(self):
        seq = DocumentSequence.objects.create(
            document_type="ITEM", prefix="ITM", include_year=False, next_number=1, padding=4
        )
        number = DocumentSequence.get_next("ITEM")
        self.assertEqual(number, "ITM-0001")


class AccountsAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="apiuser", password="apipass123"
        )

    def test_login_endpoint(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "apiuser", "password": "apipass123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "apiuser")

    def test_login_endpoint_invalid(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "apiuser", "password": "wrong"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_me_endpoint_requires_auth(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 403)

    def test_me_endpoint_authenticated(self):
        self.client.login(username="apiuser", password="apipass123")
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["username"], "apiuser")

    def test_users_endpoint(self):
        self.client.login(username="apiuser", password="apipass123")
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(u["username"] == "apiuser" for u in response.json()))

    def test_users_endpoint_denied_without_permission(self):
        regular = User.objects.create_user(username="regular", password="pass12345")
        self.client.login(username="regular", password="pass12345")
        response = self.client.get("/api/users/")
        self.assertEqual(response.status_code, 403)

    def test_groups_endpoint(self):
        self.client.login(username="apiuser", password="apipass123")
        response = self.client.get("/api/groups/")
        self.assertEqual(response.status_code, 200)

    def test_permissions_endpoint(self):
        self.client.login(username="apiuser", password="apipass123")
        response = self.client.get("/api/permissions/")
        self.assertEqual(response.status_code, 200)

    def test_company_settings_api(self):
        self.client.login(username="apiuser", password="apipass123")
        response = self.client.get("/api/company-settings/")
        self.assertEqual(response.status_code, 200)