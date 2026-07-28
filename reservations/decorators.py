from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

GROUPE_ADMIN = "Administrateurs"
GROUPE_AGENT = "Agents guichet"


def est_administrateur(user):
    return user.is_authenticated and user.is_staff and (
        user.is_superuser or user.groups.filter(name=GROUPE_ADMIN).exists()
    )


def est_agent_ou_admin(user):
    return user.is_authenticated and user.is_staff and (
        user.is_superuser
        or user.groups.filter(name__in=[GROUPE_ADMIN, GROUPE_AGENT]).exists()
    )


def admin_required(view_func):
    """Réservé aux administrateurs : gestion des lignes, bateaux, traversées, statistiques."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.warning(request, "Merci de vous connecter pour accéder au back-office SILIMU.")
            return redirect('admin_login')
        if not est_administrateur(request.user):
            messages.error(request, "Cette page est réservée aux administrateurs.")
            return redirect('admin_comptoir')
        return view_func(request, *args, **kwargs)
    return wrapper


def agent_required(view_func):
    """Accessible aux agents guichet ET aux administrateurs : comptoir, liste des réservations."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.warning(request, "Merci de vous connecter pour accéder au back-office SILIMU.")
            return redirect('admin_login')
        if not est_agent_ou_admin(request.user):
            messages.error(request, "Ce compte n'a pas accès au back-office.")
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------
# Compte passager (espace public, authentification par session — distincte
# du système de comptes du back-office qui utilise django.contrib.auth)
# ---------------------------------------------------------------------

def passager_connecte(request):
    """Retourne l'objet Passager actuellement connecté (session), ou None."""
    from .models import Passager
    passager_id = request.session.get('passager_id')
    if not passager_id:
        return None
    return Passager.objects.filter(pk=passager_id).first()


def passager_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not passager_connecte(request):
            messages.warning(request, "Merci de vous connecter à votre compte passager.")
            return redirect('compte_connexion')
        return view_func(request, *args, **kwargs)
    return wrapper
