from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

from reservations.decorators import GROUPE_ADMIN, GROUPE_AGENT


class Command(BaseCommand):
    help = "Crée les groupes de rôles du back-office : Administrateurs et Agents guichet."

    def handle(self, *args, **options):
        for nom in (GROUPE_ADMIN, GROUPE_AGENT):
            group, created = Group.objects.get_or_create(name=nom)
            statut = "créé" if created else "déjà existant"
            self.stdout.write(self.style.SUCCESS(f"Groupe « {nom} » {statut}."))

        self.stdout.write(self.style.SUCCESS(
            "\nPour donner un rôle à un utilisateur :\n"
            "  python manage.py shell\n"
            "  >>> from django.contrib.auth.models import User, Group\n"
            "  >>> u = User.objects.get(username='...')\n"
            "  >>> u.is_staff = True; u.save()\n"
            "  >>> u.groups.add(Group.objects.get(name='Agents guichet'))\n"
            "(remplacer par 'Administrateurs' pour un accès complet)"
        ))
