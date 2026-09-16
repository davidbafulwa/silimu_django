import base64
from io import BytesIO

import qrcode
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def qr_code_png(data):
    """Retourne les octets PNG du QR code pour `data`."""
    img = qrcode.make(data, box_size=12, border=2)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def qr_code_base64(data):
    """Génère un QR code encodant `data` et le renvoie en base64 (utilisable dans <img src="data:...">)."""
    img = qrcode.make(data, box_size=6, border=2)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def envoyer_billet_email(reservation):
    """
    Envoie le billet par e-mail au passager s'il a renseigné une adresse.
    Ne fait rien silencieusement si aucune adresse n'est fournie, ou si
    l'envoi échoue (le billet reste de toute façon consultable en ligne).
    """
    if not reservation.email:
        return False

    sujet = f"Votre billet SILIMU — {reservation.code}"
    contexte = {"reservation": reservation}
    texte = render_to_string("reservations/email/billet.txt", contexte)
    html = render_to_string("reservations/email/billet.html", contexte)

    try:
        message = EmailMultiAlternatives(
            sujet, texte, settings.DEFAULT_FROM_EMAIL, [reservation.email]
        )
        message.attach_alternative(html, "text/html")
        message.attach(
            f"billet-{reservation.code}.png",
            qr_code_png(reservation.code),
            "image/png",
        )
        message.send(fail_silently=False)
        reservation.billet_envoye = True
        reservation.save(update_fields=['billet_envoye'])
        return True
    except Exception:
        return False


def envoyer_annulation_email(reservation):
    """
    Envoie un e-mail d'annulation au passager s'il a renseigné une adresse.
    Procède silencieusement en cas d'échec : l'annulation reste effective.
    """
    if not reservation.email:
        return False

    sujet = f"Votre réservation SILIMU a été annulée ({reservation.code})"
    contexte = {"reservation": reservation}
    texte = render_to_string("reservations/email/annulation.txt", contexte)
    html = render_to_string("reservations/email/annulation.html", contexte)

    try:
        message = EmailMultiAlternatives(
            sujet, texte, settings.DEFAULT_FROM_EMAIL, [reservation.email]
        )
        message.attach_alternative(html, "text/html")
        message.send(fail_silently=False)
        return True
    except Exception:
        return False


def envoyer_rappel_email(reservation):
    """Envoie un e-mail de rappel avant le départ (une seule fois par réservation)."""
    if not reservation.email or reservation.rappel_envoye:
        return False

    sujet = f"Rappel — votre traversée SILIMU approche ({reservation.code})"
    contexte = {"reservation": reservation}
    texte = render_to_string("reservations/email/rappel.txt", contexte)
    html = render_to_string("reservations/email/rappel.html", contexte)

    try:
        message = EmailMultiAlternatives(
            sujet, texte, settings.DEFAULT_FROM_EMAIL, [reservation.email]
        )
        message.attach_alternative(html, "text/html")
        message.send(fail_silently=False)
        reservation.rappel_envoye = True
        reservation.save(update_fields=['rappel_envoye'])
        return True
    except Exception:
        return False


def alerter_admin_traversee_pleine(traversee):
    """
    Envoie un e-mail à l'équipe SILIMU quand une traversée atteint le seuil
    d'alerte de remplissage (une seule fois par traversée).
    """
    if traversee.alerte_remplissage_envoyee:
        return False
    if not settings.ADMIN_EMAIL:
        return False
    if traversee.taux_remplissage() < settings.SEUIL_ALERTE_REMPLISSAGE:
        return False

    sujet = f"[SILIMU] Traversée bientôt complète — {traversee.route} du {traversee.date}"
    corps = (
        f"La traversée {traversee.route} du {traversee.date} à {traversee.heure} "
        f"({traversee.bateau.nom}) est remplie à {traversee.taux_remplissage()}%.\n"
        f"Places restantes : {traversee.places_disponibles()} / {traversee.bateau.capacite}.\n\n"
        f"Pensez à programmer une traversée supplémentaire si besoin."
    )
    try:
        from django.core.mail import send_mail
        send_mail(sujet, corps, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL], fail_silently=False)
        traversee.alerte_remplissage_envoyee = True
        traversee.save(update_fields=['alerte_remplissage_envoyee'])
        return True
    except Exception:
        return False
