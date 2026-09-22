from django.core.management.base import BaseCommand
from django.utils import timezone

from reservations.models import Reservation


class Command(BaseCommand):
    help = (
        "Marque comme « ÉCHEC » les réservations EN ATTENTE dont le délai de "
        "paiement est dépassé : leurs places sont ainsi libérées. À planifier "
        "périodiquement (ex: toutes les 5 minutes) via cron."
    )

    def handle(self, *args, **options):
        maintenant = timezone.now()
        nb = Reservation.objects.filter(
            statut=Reservation.Statut.EN_ATTENTE,
            expire_le__lt=maintenant,
        ).update(statut=Reservation.Statut.ECHEC, expire_le=None)

        self.stdout.write(
            self.style.SUCCESS(
                f"{nb} réservation(s) expirée(s) : place(s) libérée(s)."
            )
        )