import random
from datetime import timedelta, time

from django.core.management.base import BaseCommand
from django.utils import timezone

from reservations.models import Route, Bateau, Traversee


ROUTES = [
    ("Munyaga", "Kasenyi", 38, 75),
    ("Munyaga", "Ilanga", 22, 45),
    ("Kasenyi", "Rutongo", 51, 100),
    ("Ilanga", "Bandari-Nord", 29, 55),
]

BATEAUX = [
    ("MV Kivu Étoile", 80, Bateau.TypeBateau.VEDETTE),
    ("MV Perle du Lac", 120, Bateau.TypeBateau.FERRY),
    ("MV Aube Bleue", 60, Bateau.TypeBateau.VEDETTE),
]

HORAIRES = [time(7, 30), time(13, 0), time(17, 15)]


class Command(BaseCommand):
    help = "Insère des données de démonstration : lignes, bateaux et traversées SILIMU."

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help="Supprime les lignes, bateaux et traversées existants avant de les recréer."
        )

    def handle(self, *args, **options):
        if options['reset']:
            Traversee.objects.all().delete()
            Bateau.objects.all().delete()
            Route.objects.all().delete()
            self.stdout.write(self.style.WARNING("Anciennes données supprimées."))

        routes = []
        for depart, arrivee, dist, duree in ROUTES:
            route, _ = Route.objects.get_or_create(
                port_depart=depart, port_arrivee=arrivee,
                defaults={'distance_km': dist, 'duree_min': duree}
            )
            routes.append(route)

        bateaux = []
        for nom, capacite, type_bateau in BATEAUX:
            bateau, _ = Bateau.objects.get_or_create(
                nom=nom, defaults={'capacite': capacite, 'type_bateau': type_bateau}
            )
            bateaux.append(bateau)

        today = timezone.localdate()
        created = 0
        for d in range(5):
            date = today + timedelta(days=d)
            for i, route in enumerate(routes):
                bateau = bateaux[(i + d) % len(bateaux)]
                for ti, heure in enumerate(HORAIRES):
                    prix = 8000 + route.distance_km * 120 + ti * 500
                    _, was_created = Traversee.objects.get_or_create(
                        route=route, bateau=bateau, date=date, heure=heure,
                        defaults={'prix': prix}
                    )
                    if was_created:
                        created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Données SILIMU prêtes : {len(routes)} ligne(s), {len(bateaux)} bateau(x), "
            f"{created} traversée(s) créée(s)."
        ))
