from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from reservations.models import Reservation
from reservations.notifications import envoyer_rappel_email


class Command(BaseCommand):
    help = (
        "Envoie un e-mail de rappel aux passagers dont le départ approche "
        "(seuil configurable via RAPPEL_HEURES_AVANT). À planifier périodiquement "
        "(ex: toutes les heures) via cron ou le Planificateur de tâches Windows."
    )

    def handle(self, *args, **options):
        maintenant = timezone.now()
        horizon = maintenant + timedelta(hours=settings.RAPPEL_HEURES_AVANT)

        candidats = Reservation.objects.filter(
            statut=Reservation.Statut.CONFIRME,
            rappel_envoye=False,
        ).exclude(email='').select_related('traversee')

        envoyes = 0
        for reservation in candidats:
            depart = reservation.traversee.date_heure_depart()
            if maintenant <= depart <= horizon:
                if envoyer_rappel_email(reservation):
                    envoyes += 1

        self.stdout.write(self.style.SUCCESS(
            f"{envoyes} rappel(s) envoyé(s) pour les départs dans les {settings.RAPPEL_HEURES_AVANT}h."
        ))
