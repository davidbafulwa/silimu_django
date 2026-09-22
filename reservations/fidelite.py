"""Programme de fidélité SILIMU : tous les 10 voyages effectués, un billet
gratuit. L'attribution est automatique à l'embarquement : un e-mail part tout
seul au dernier e-mail utilisé par le passager et l'équipe SILIMU reçoit une
notification interne visible dans le back-office."""

from django.utils import timezone

from .models import Reservation, RecompenseFidelite, NotificationInterne

SEUIL_FIDELITE = 10


def compter_voyages(telephone):
    """Nombre de voyages réellement effectués (billets EMBARQUÉS) pour un numéro."""
    if not telephone:
        return 0
    return Reservation.objects.filter(
        telephone=telephone, statut=Reservation.Statut.EMBARQUE
    ).count()


def dernier_email(telephone):
    """Dernier e-mail renseigné par ce passager (utile pour la récompense)."""
    derniere = (
        Reservation.objects.filter(telephone=telephone)
        .exclude(email='')
        .order_by('-date_creation')
        .first()
    )
    return derniere.email if derniere else ''


def attribuer_recompense(telephone):
    """À appeler après chaque embarquement : crée automatiquement la récompense
    du palier atteint (10, 20, 30...), envoie l'e-mail au dernier e-mail connu
    et crée une notification visible par l'équipe SILIMU. Ne fait rien si le
    palier n'est pas atteint ou déjà récompensé."""
    if not telephone:
        return None
    total = compter_voyages(telephone)
    if total < SEUIL_FIDELITE:
        return None
    palier = (total // SEUIL_FIDELITE) * SEUIL_FIDELITE
    if RecompenseFidelite.objects.filter(telephone=telephone, seuil=palier).exists():
        return None
    email = dernier_email(telephone)

    recompense = None
    from .models import generer_code_fidelite
    for _ in range(3):
        code = generer_code_fidelite()
        if not RecompenseFidelite.objects.filter(code=code).exists():
            recompense = RecompenseFidelite.objects.create(
                code=code, telephone=telephone, email=email or '', seuil=palier,
            )
            break
    if recompense is None:
        return None

    NotificationInterne.objects.create(
        type=NotificationInterne.Type.FIDELITE,
        message=f"Voyage n°{palier} atteint : billet gratuit à remettre ({recompense.code}).",
        detail=(
            f"{recompense.telephone} a effectué {palier} voyages SILIMU embarques. "
            f"La recompense {recompense.code} a été attribuée automatiquement "
            f"et envoyée au dernier e-mail connu ({recompense.email or 'aucun'})."
        ),
        telephone=telephone,
        recompense=recompense,
    )

    if email:
        from .notifications import envoyer_recompense_email
        if envoyer_recompense_email(recompense):
            recompense.envoye_le = timezone.now()
            recompense.save(update_fields=['envoye_le'])
    return recompense