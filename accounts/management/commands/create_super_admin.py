import getpass
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Create the Super Admin account (used during installation)"

    def add_arguments(self, parser):
        parser.add_argument("--username", default=None)
        parser.add_argument("--email", default="")
        parser.add_argument("--password", default=None)

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING("A superuser already exists. Skipping creation.")
            )
            return

        username = options["username"] or input("Super admin username [admin]: ") or "admin"
        email = options["email"] or input("Super admin email: ").strip()
        password = options["password"]
        if not password:
            password = getpass.getpass("Super admin password: ")

        user = User.objects.create_superuser(
            username=username, email=email, password=password
        )
        self.stdout.write(
            self.style.SUCCESS(f"Super admin '{username}' created successfully.")
        )