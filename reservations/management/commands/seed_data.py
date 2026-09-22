import random
from datetime import timedelta, time

from django.core.management.base import BaseCommand
from django.utils import timezone

from reservations.models import Port, Route, Bateau, Traversee


ROUTES = [
    # Lac Kivu — entre Sud-Kivu et Nord-Kivu
    ("Bukavu", "Goma", 100, 90),
    ("Goma", "Bukavu", 100, 90),
    ("Bukavu", "Idjwi", 45, 60),
    ("Idjwi", "Bukavu", 45, 60),
    ("Goma", "Minova", 55, 70),
    ("Minova", "Goma", 55, 70),
    ("Bukavu", "Kalehe", 35, 50),
    ("Kalehe", "Bukavu", 35, 50),
    # Lac Tanganyika — extrémité sud du Sud-Kivu
    ("Uvira", "Kalemie", 120, 150),
    ("Kalemie", "Uvira", 120, 150),
]

BATEAUX = [
    ("MV Kivu Étoile", 80, Bateau.TypeBateau.VEDETTE),
    ("MV Perle du Lac", 120, Bateau.TypeBateau.FERRY),
    ("MV Aube Bleue", 60, Bateau.TypeBateau.VEDETTE),
    ("MV Virunga", 100, Bateau.TypeBateau.VEDETTE),
    ("MV Idjwi Express", 70, Bateau.TypeBateau.VEDETTE),
    ("MV Mapendo", 45, Bateau.TypeBateau.PIROGUE),
]

HORAIRES = [time(7, 0), time(9, 30), time(13, 0), time(17, 0)]


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

        # ── Ports ──────────────────────────────────────────────────────
        ports = {}
        for nom in ("Bukavu", "Goma", "Idjwi", "Minova", "Kalehe", "Uvira", "Kalemie"):
            port, _ = Port.objects.get_or_create(nom=nom, defaults={'est_actif': True})
            ports[nom] = port

        routes = []
        for depart, arrivee, dist, duree in ROUTES:
            route, _ = Route.objects.get_or_create(
                port_depart=ports[depart], port_arrivee=ports[arrivee],
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
