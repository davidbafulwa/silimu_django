from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .supabase_client import get_user


class SupabaseAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            return None

        if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
            return None

        supabase_user = get_user(token)
        if supabase_user is None:
            raise AuthenticationFailed("Token Supabase invalide ou expiré")

        email = (supabase_user.email or "").lower().strip()
        phone = supabase_user.phone or ""

        from .models import Passager
        passager = None

        if email:
            passager = Passager.objects.filter(email__iexact=email).first()
        if not passager and phone:
            passager = Passager.objects.filter(telephone=phone).first()

        if not passager:
            nom = ""
            metadata = supabase_user.user_metadata or {}
            nom = metadata.get("full_name") or metadata.get("nom_complet") or ""
            passager = Passager(
                nom_complet=nom or email.split("@")[0] if email else "Passager Supabase",
                telephone=phone or email or "",
                email=email,
            )
            passager.definir_mot_de_passe("")  # mot de passe vide (auth via Supabase)
            passager.save()

        return (passager, token)
