"""
Service de réservation — garantie d'intégrité des places.

Le calcul des places disponibles (`places_reservées()` est évalué à la volée)
souffre d'une course critique : deux requêtes simultanées (deux agents au
comptoir, ou un agent + un passager en ligne) peuvent toutes les deux valider
une disponibilité avant l'une des deux d'enregistrer. Résultat : surbooking.

La solution : verrouiller la ligne de la traversée (`select_for_update`)
à l'intérieur d'une transaction atomique, puis vérifier ET créer la
réservation dans ce même verrou. Sur PostgreSQL ce verrou est réel ; sur
SQLite (tests) il est ignoré, ce qui reste sans conséquence pour les tests.
"""
from decimal import Decimal

from django.db import transaction

from .models import Traversee, Reservation


class SurbookingError(Exception):
    """Plus assez de places disponibles au moment de l'enregistrement."""


def reserver_place(traversee, nb_places, statut=None, **champs):
    """
    Crée une réservation de façon atomique.

    - verrouille la traversée (aucune autre écriture concurrente possible pendant la vérif)
    - vérifie la disponibilité sous ce verrou
    - crée la réservation en calculant le total avec le prix verrouillé

    Lève `SurbookingError` si les places ont été prises entre-temps.
    """
    with transaction.atomic():
        verrou = Traversee.objects.select_for_update().get(pk=traversee.pk)
        if nb_places > verrou.places_disponibles():
            raise SurbookingError(
                f"Il ne reste que {verrou.places_disponibles()} place(s) disponible(s) "
                f"sur cette traversée."
            )
        champs.pop('total', None)  # le total est recalculé ici pour rester cohérent
        champs.pop('statut', None)
        reservation = Reservation.objects.create(
            traversee=verrou,
            statut=statut or Reservation.Statut.EN_ATTENTE,
            total=Decimal(nb_places) * verrou.prix,
            nb_places=nb_places,
            **champs,
        )
    return reservation