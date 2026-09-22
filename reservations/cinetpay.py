"""
Intégration CinetPay (agrégateur de paiement Mobile Money / carte bancaire).

CinetPay permet d'accepter Orange Money, Airtel Money, M-Pesa et les cartes
bancaires via une seule API, disponible en RDC et dans plusieurs pays
d'Afrique francophone. Documentation officielle : https://docs.cinetpay.com

Pour activer les paiements réels, il faut :
1. Créer un compte marchand sur https://www.cinetpay.com
2. Récupérer APIKEY et SITE_ID dans le menu "Intégrations" du tableau de bord
3. Renseigner les variables d'environnement CINETPAY_API_KEY et CINETPAY_SITE_ID
4. S'assurer que le site est joignable en HTTPS depuis Internet pour que
   CinetPay puisse appeler l'URL de notification.
"""
import requests
from django.conf import settings

INIT_URL = "https://api-checkout.cinetpay.com/v2/payment"
CHECK_URL = "https://api-checkout.cinetpay.com/v2/payment/check"

# Le canal envoyé à CinetPay en fonction du mode choisi par le passager.
CHANNELS_PAR_MODE = {
    "ORANGE_MONEY": "MOBILE_MONEY",
    "AIRTEL_MONEY": "MOBILE_MONEY",
    "MPESA": "MOBILE_MONEY",
    "CARTE": "CREDIT_CARD",
}


class CinetPayError(Exception):
    """Levée quand CinetPay refuse ou ne peut pas traiter la demande."""


def est_configure():
    """True si les identifiants marchand CinetPay sont renseignés."""
    return bool(settings.CINETPAY_API_KEY and settings.CINETPAY_SITE_ID)


def _build_absolute_url(request, path):
    return request.build_absolute_uri(path)


def initier_paiement(reservation, request):
    """
    Démarre une transaction CinetPay pour une réservation et renvoie
    l'URL de paiement vers laquelle rediriger le passager.
    """
    if not settings.CINETPAY_API_KEY or not settings.CINETPAY_SITE_ID:
        raise CinetPayError(
            "CINETPAY_API_KEY / CINETPAY_SITE_ID ne sont pas configurés. "
            "Voir README.md section Paiement Mobile Money."
        )

    payload = {
        "apikey": settings.CINETPAY_API_KEY,
        "site_id": settings.CINETPAY_SITE_ID,
        "transaction_id": reservation.code,
        "amount": int(reservation.total),
        "currency": settings.CINETPAY_CURRENCY,
        "description": f"Billet SILIMU {reservation.traversee.route} - {reservation.nb_places} place(s)",
        "customer_name": reservation.nom_passager.split(" ")[0] or reservation.nom_passager,
        "customer_surname": " ".join(reservation.nom_passager.split(" ")[1:]) or reservation.nom_passager,
        "customer_phone_number": reservation.telephone,
        "notify_url": _build_absolute_url(request, "/paiement/notification/"),
        "return_url": _build_absolute_url(request, f"/paiement/retour/{reservation.code}/"),
        "channels": CHANNELS_PAR_MODE.get(reservation.mode_paiement, "ALL"),
        "metadata": reservation.code,
        "lang": "FR",
    }

    try:
        response = requests.post(INIT_URL, json=payload, timeout=15)
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise CinetPayError(f"Impossible de contacter CinetPay : {exc}") from exc

    if data.get("code") != "201":
        raise CinetPayError(data.get("description") or data.get("message") or "Échec de l'initialisation du paiement.")

    return data["data"]["payment_url"]


def verifier_paiement(transaction_id):
    """
    Interroge CinetPay pour connaître le vrai statut d'une transaction.
    À utiliser systématiquement (ne jamais faire confiance au seul appel
    de notification, conformément à la documentation CinetPay).
    """
    payload = {
        "apikey": settings.CINETPAY_API_KEY,
        "site_id": settings.CINETPAY_SITE_ID,
        "transaction_id": transaction_id,
    }
    try:
        response = requests.post(CHECK_URL, json=payload, timeout=15)
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise CinetPayError(f"Impossible de vérifier la transaction : {exc}") from exc


def paiement_accepte(verification_data):
    """True si la réponse de vérification CinetPay indique un paiement réussi."""
    data = verification_data.get("data", {})
    return (
        verification_data.get("code") in ("00", 0, "0")
        and data.get("status") == "ACCEPTED"
    )
