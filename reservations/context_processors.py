from .decorators import est_administrateur, passager_connecte


def role_utilisateur(request):
    return {
        'is_admin': est_administrateur(request.user) if request.user.is_authenticated else False,
        'passager': passager_connecte(request),
    }
