from django import template
from reservations.notifications import qr_code_base64

register = template.Library()


@register.filter
def qr_code(value):
    """Utilisation dans un template : {{ reservation.code|qr_code }} -> chaîne base64 PNG."""
    return qr_code_base64(str(value))


@register.filter
def dict_get(d, key):
    """Accès à une clé d'un dictionnaire depuis un template : {{ prix|dict_get:"Goma" }}."""
    if d is None:
        return ''
    return d.get(key, '')
