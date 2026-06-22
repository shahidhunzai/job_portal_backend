from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Create the initial Super Admin user (admin / admin@rdi.com)."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="admin")
        parser.add_argument("--email", default="admin@rdi.com")
        parser.add_argument("--password", default="rdi@123")
        parser.add_argument("--user_type", default="super_admin")

    def handle(self, *args, **options):
        User = get_user_model()

        username = options["username"]
        email = options["email"].lower()
        password = options["password"]
        user_type = options["user_type"]

        # Create (or fetch) by username.
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "user_type": user_type,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )

        # If the user existed but data is missing/outdated, normalize it.
        updated = False
        if user.email.lower() != email:
            user.email = email
            updated = True
        if getattr(user, "user_type", None) != user_type:
            user.user_type = user_type
            updated = True
        if not user.is_staff:
            user.is_staff = True
            updated = True
        if not user.is_superuser:
            user.is_superuser = True
            updated = True
        if not user.is_active:
            user.is_active = True
            updated = True

        if created:
            user.set_password(password)
            updated = True
        else:
            # Ensure password is set to the given value.
            user.set_password(password)
            updated = True

        if updated:
            user.save()

        self.stdout.write(self.style.SUCCESS(
            f"Super Admin ready: username={user.username}, email={user.email}"
        ))

