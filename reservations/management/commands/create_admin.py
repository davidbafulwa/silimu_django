import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Crée ou met à jour le superutilisateur (Espace pro / admin Django) "
        "à partir des variables d'environnement DJANGO_ADMIN_USER, "
        "DJANGO_ADMIN_EMAIL et DJANGO_ADMIN_PASSWORD (défauts : admin / admin)."
    )

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_ADMIN_USER', 'admin')
        email = os.environ.get('DJANGO_ADMIN_EMAIL', 'admin@silimu.local')
        password = os.environ.get('DJANGO_ADMIN_PASSWORD', 'admin')

        user, created = User.objects.get_or_create(
            username=username, defaults={'email': email, 'is_staff': True, 'is_superuser': True}
        )
        if not created:
            user.email = email
            user.is_staff = True
            user.is_superuser = True
        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f"Superutilisateur '{username}' {'créé' if created else 'mis à jour'}."
        ))