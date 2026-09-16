import csv
from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Sum, Q, Count, Min
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import cinetpay
from .auth_backends import SupabaseAuthentication
from .decorators import admin_required, agent_required, est_administrateur, passager_connecte, passager_required
from .forms import (
    RechercheForm, ReservationForm, ReservationComptoirForm, MesBilletsForm,
    RouteForm, BateauForm, TraverseeForm,
    PassagerInscriptionForm, PassagerConnexionForm,
)
from .models import Route, Bateau, Traversee, Reservation, Passager
from .notifications import envoyer_billet_email, alerter_admin_traversee_pleine
from .supabase_client import sign_up as supabase_sign_up, sign_in as supabase_sign_in, sign_out as supabase_sign_out


# ---------------------------------------------------------------------
# Espace public — recherche & réservation
# ---------------------------------------------------------------------

def home(request):
    form = RechercheForm(request.GET or None)
    resultats = None

    if request.GET:
        traversees = Traversee.objects.select_related('route', 'bateau').filter(
            date__gte=timezone.localdate(),
            bateau__en_service=True,  # un bateau en maintenance n'est jamais proposé
        )
        if form.is_valid():
            depart = form.cleaned_data.get('depart')
            arrivee = form.cleaned_data.get('arrivee')
            date = form.cleaned_data.get('date')
            if depart:
                traversees = traversees.filter(route__port_depart=depart)
            if arrivee:
                traversees = traversees.filter(route__port_arrivee=arrivee)
            if date:
                traversees = traversees.filter(date=date)
        resultats = traversees.order_by('date', 'heure')

    ports = sorted(set(
        list(Route.objects.values_list('port_depart', flat=True)) +
        list(Route.objects.values_list('port_arrivee', flat=True))
    ))

    # Prochains départs (vitrine "en direct") + tarifs "à partir de" par port
    aujourdhui = timezone.localdate()
    prochains = Traversee.objects.select_related('route', 'bateau').filter(
        date__gte=aujourdhui, bateau__en_service=True
    ).order_by('date', 'heure')[:5]

    a_futur = Traversee.objects.filter(date__gte=aujourdhui, bateau__en_service=True)
    prix_par_port = {}
    for ligne in a_futur.values('route__port_depart').annotate(prix_min=Min('prix')):
        prix_par_port[ligne['route__port_depart']] = ligne['prix_min']
    for ligne in a_futur.values('route__port_arrivee').annotate(prix_min=Min('prix')):
        prix_par_port.setdefault(ligne['route__port_arrivee'], ligne['prix_min'])

    stats_marketing = {
        'ports': len(ports),
        'bateaux': Bateau.objects.filter(en_service=True).count(),
        'lignes': Route.objects.count(),
        'departs_aujourdhui': Traversee.objects.filter(date=aujourdhui, bateau__en_service=True).count(),
    }

    # ── Contenus marketing de la page d'accueil ─────────────────────────
    trust = [
        {'icon': '🔒', 'title': 'Paiement sécurisé', 'sub': 'Orange, Airtel, M-Pesa, carte'},
        {'icon': '🎫', 'title': 'E-billet QR code', 'sub': 'Imprimable & envoyé par e-mail'},
        {'icon': '🕐', 'title': 'Places en direct', 'sub': 'Mise à jour temps réel'},
        {'icon': '📞', 'title': 'Support local', 'sub': 'Bukavu & Goma, 7j/7'},
    ]
    etapes = [
        {'num': '1', 'title': 'Recherchez', 'text': 'Choisissez vos ports de départ et d’arrivée, votre date et le nombre de places.'},
        {'num': '2', 'title': 'Réglez', 'text': 'Payez en toute sécurité par Mobile Money (Orange, Airtel, M-Pesa) ou carte bancaire.'},
        {'num': '3', 'title': 'Recevez', 'text': 'Votre e-billet avec QR code arrive instantanément par e-mail après confirmation.'},
        {'num': '4', 'title': 'Embarquez', 'text': 'Présentez votre billet (écran ou imprimé) au guichet le jour du départ.'},
    ]
    destinations = [
        {'nom': 'Bukavu', 'arrivee': 'Bukavu', 'img': 'img/kivu.jpg',
         'tagline': 'Capitale du Sud-Kivu', 'duree': 'départs quotidiens'},
        {'nom': 'Goma', 'arrivee': 'Goma', 'img': 'img/goma.jpg',
         'tagline': 'Porte du Nord-Kivu', 'duree': 'au pied du volcan'},
        {'nom': 'Idjwi', 'arrivee': 'Idjwi', 'img': 'img/aerial.jpg',
         'tagline': 'La grande île du lac Kivu', 'duree': 'escapade nature'},
        {'nom': 'Minova', 'arrivee': 'Minova', 'img': 'img/berges.jpg',
         'tagline': 'Nord-Kivu Sud', 'duree': 'traversées régulières'},
        {'nom': 'Kalehe', 'arrivee': 'Kalehe', 'img': 'img/lac_vert.jpg',
         'tagline': 'Berceaux verts du Kivu', 'duree': 'à l’est du lac'},
        {'nom': 'Uvira ⇄ Kalemie', 'arrivee': 'Kalemie', 'img': 'img/bateau_bois.jpg',
         'tagline': 'Sur le lac Tanganyika', 'duree': 'Sud-Kivu / Tanganyika'},
    ]
    for d in destinations:
        d['prix_min'] = prix_par_port.get(d['arrivee'])
    atouts = [
        {'icon': '✅', 'title': 'Tarifs sans surprises', 'text': 'Le prix affiché est le prix payé, en francs congolais, tous frais inclus.'},
        {'icon': '📲', 'title': 'Paiement Mobile Money', 'text': 'Orange Money, Airtel Money et M-Pesa pris en charge, ou en espèces au comptoir.'},
        {'icon': '🧾', 'title': 'Billet QR scannable', 'text': 'Un QR code unique par billet : contrôle rapide et sans papier à l’embarquement.'},
        {'icon': '🔁', 'title': 'Annulation simple', 'text': 'Retrouvez et annulez vos billets depuis votre compte passager.'},
    ]
    temoignages = [
        {'nom': 'Chantal M.', 'detail': 'Trajet Bukavu → Goma', 'texte': 'Réservé en ligne le matin, embarqué l’après-midi. Le billet QR m’a été envoyé direct sur mon e-mail, génial !'},
        {'nom': 'Patient K.', 'detail': 'Trajet Goma → Minova', 'texte': 'Enfin des billets sans faire la queue au guichet. J’ai payé avec M-Pesa en 1 minute.'},
        {'nom': 'Grâce N.', 'detail': 'Trajet vers Idjwi', 'texte': 'Comptoir accueillant à Bukavu et bateaux propres. Je recommande l’option e-billet imprimable.'},
    ]
    faq = [
        {'q': 'Comment recevoir mon billet ?', 'a': 'Dès que votre paiement est confirmé, votre e-billet avec QR code est envoyé automatiquement à votre adresse e-mail. Vous pouvez aussi le retrouver en ligne grâce à votre code ou via votre compte passager.'},
        {'q': 'Quels moyens de paiement sont acceptés ?', 'a': 'Orange Money, Airtel Money, M-Pesa et carte bancaire via une passerelle sécurisée. Vous pouvez aussi régler en espèces à nos guichets de Bukavu et de Goma.'},
        {'q': 'Que se passe-t-il si ma traversée est annulée ?', 'a': 'Notre équipe vous contacte par téléphone ou e-mail et vous propose un report sur la traversée suivante ou un remboursement intégral.'},
        {'q': 'Puis-je réserver pour plusieurs personnes ?', 'a': 'Oui, indiquez simplement le nombre de places souhaité au moment de la réservation. Le total s’ajuste automatiquement.'},
        {'q': 'Dois-je imprimer mon billet ?', 'a': 'Non. Présentez votre QR code depuis votre téléphone à l’embarquement. L’impression reste disponible si vous préférez.'},
    ]

    return render(request, 'reservations/home.html', {
        'form': form,
        'resultats': resultats,
        'ports': ports,
        'prochains': prochains,
        'prix_par_port': prix_par_port,
        'stats_marketing': stats_marketing,
        'trust': trust,
        'etapes': etapes,
        'destinations': destinations,
        'atouts': atouts,
        'temoignages': temoignages,
        'faq': faq,
    })


def passager_lookup(request, telephone):
    """API légère utilisée par le formulaire de réservation pour retrouver
    automatiquement le nom d'un passager déjà venu (historique des passagers)."""
    nom = Reservation.nom_pour_telephone(telephone)
    return JsonResponse({'nom': nom})


def reserver(request, traversee_id):
    traversee = get_object_or_404(Traversee.objects.select_related('route', 'bateau'), pk=traversee_id)
    passager = passager_connecte(request)

    if request.method == 'POST':
        form = ReservationForm(request.POST, traversee=traversee)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.traversee = traversee
            reservation.total = Decimal(reservation.nb_places) * traversee.prix
            reservation.statut = Reservation.Statut.EN_ATTENTE
            if passager:
                reservation.passager = passager
            reservation.save()

            # ── Paiement au guichet (espèces) : pas de CinetPay, le passager
            #    viendra régler et il recevra son billet une fois encaissé. ──
            if reservation.mode_paiement == Reservation.ModePaiement.ESPECES:
                messages.success(
                    request,
                    "Réservation enregistrée ! Présentez-vous au guichet SILIMU avec le code "
                    f"{reservation.code} pour régler et recevoir votre billet.",
                )
                return redirect('billet', code=reservation.code)

            try:
                payment_url = cinetpay.initier_paiement(reservation, request)
            except cinetpay.CinetPayError as exc:
                reservation.marquer_echec()
                messages.error(
                    request,
                    f"Le paiement n'a pas pu être initié ({exc}). Réessayez ou contactez SILIMU."
                )
                return redirect('reserver', traversee_id=traversee.id)

            return redirect(payment_url)
    else:
        initial = {}
        if passager:
            initial = {'nom_passager': passager.nom_complet, 'telephone': passager.telephone, 'email': passager.email}
        form = ReservationForm(traversee=traversee, initial=initial)

    return render(request, 'reservations/reservation_form.html', {
        'form': form,
        'traversee': traversee,
        'passager': passager,
    })


def _finaliser_si_payee(reservation):
    """Actions déclenchées une seule fois quand une réservation devient confirmée :
    envoi du billet par e-mail + alerte de remplissage à l'équipe SILIMU."""
    if reservation.statut == Reservation.Statut.CONFIRME:
        if not reservation.billet_envoye:
            envoyer_billet_email(reservation)
        alerter_admin_traversee_pleine(reservation.traversee)


@csrf_exempt
@require_POST
def paiement_notification(request):
    """
    Appelée directement par les serveurs de CinetPay pour signaler le
    résultat d'un paiement. On ne fait jamais confiance à ce POST seul :
    on revérifie systématiquement le statut via l'API "check" de CinetPay.
    """
    transaction_id = request.POST.get('cpm_trans_id') or request.POST.get('transaction_id')
    if not transaction_id:
        return HttpResponseBadRequest("cpm_trans_id manquant")

    reservation = Reservation.objects.filter(code=transaction_id).first()
    if not reservation:
        return HttpResponse(status=404)

    try:
        verification = cinetpay.verifier_paiement(transaction_id)
    except cinetpay.CinetPayError:
        return HttpResponse(status=200)  # CinetPay réessaiera plus tard

    if cinetpay.paiement_accepte(verification):
        reservation.marquer_payee()
    else:
        reservation.marquer_echec()

    _finaliser_si_payee(reservation)
    return HttpResponse(status=200)


def paiement_retour(request, code):
    """
    Page où CinetPay renvoie le passager après le paiement (succès ou échec).
    Aucun traitement de statut n'est fait ici sur la seule foi du retour :
    on revérifie auprès de CinetPay pour donner un retour fiable et immédiat.
    """
    reservation = get_object_or_404(
        Reservation.objects.select_related('traversee', 'traversee__route', 'traversee__bateau'),
        code=code
    )

    if reservation.statut == Reservation.Statut.EN_ATTENTE:
        try:
            verification = cinetpay.verifier_paiement(reservation.code)
            if cinetpay.paiement_accepte(verification):
                reservation.marquer_payee()
            elif verification.get('data', {}).get('status') in ('REFUSED', 'CANCELLED'):
                reservation.marquer_echec()
        except cinetpay.CinetPayError:
            pass  # le webhook de notification confirmera plus tard

    _finaliser_si_payee(reservation)

    return render(request, 'reservations/ticket.html', {
        'reservation': reservation,
        'confirmation': True,
    })


def billet(request, code):
    reservation = get_object_or_404(
        Reservation.objects.select_related('traversee', 'traversee__route', 'traversee__bateau'),
        code=code
    )
    return render(request, 'reservations/ticket.html', {
        'reservation': reservation,
        'confirmation': True,
    })


def mes_billets(request):
    form = MesBilletsForm(request.GET or None)
    resultats = []
    if request.GET.get('q'):
        q = request.GET['q'].strip()
        resultats = Reservation.objects.select_related(
            'traversee', 'traversee__route', 'traversee__bateau'
        ).filter(Q(code__iexact=q) | Q(telephone__iexact=q))
    return render(request, 'reservations/mes_billets.html', {
        'form': form,
        'resultats': resultats,
    })


# ---------------------------------------------------------------------
# Compte passager (espace public)
# ---------------------------------------------------------------------

def compte_inscription(request):
    if passager_connecte(request):
        return redirect('compte_dashboard')

    form = PassagerInscriptionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        passager = Passager(
            nom_complet=form.cleaned_data['nom_complet'],
            telephone=form.cleaned_data['telephone'],
            email=form.cleaned_data['email'],
        )
        passager.definir_mot_de_passe(form.cleaned_data['mot_de_passe'])
        passager.save()
        # Rattache automatiquement les réservations passées faites avec ce téléphone (invité)
        Reservation.objects.filter(telephone=passager.telephone, passager__isnull=True).update(passager=passager)
        request.session['passager_id'] = passager.id
        messages.success(request, f"Bienvenue {passager.nom_complet} ! Votre compte est créé.")
        return redirect('compte_dashboard')

    return render(request, 'reservations/compte_inscription.html', {'form': form})


def compte_inscription_supabase(request):
    """Inscription passager via Supabase Auth (email + mot de passe)."""
    if passager_connecte(request):
        return redirect('compte_dashboard')

    form = PassagerInscriptionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'] or f"{form.cleaned_data['telephone']}@passager.silimu"
        user_data = {
            "nom_complet": form.cleaned_data['nom_complet'],
            "telephone": form.cleaned_data['telephone'],
        }
        response, error = supabase_sign_up(email, form.cleaned_data['mot_de_passe'], user_data)
        if error:
            messages.error(request, f"Inscription Supabase échouée : {error}")
            return render(request, 'reservations/compte_inscription.html', {'form': form})

        passager = Passager(
            nom_complet=form.cleaned_data['nom_complet'],
            telephone=form.cleaned_data['telephone'],
            email=form.cleaned_data['email'],
        )
        passager.definir_mot_de_passe(form.cleaned_data['mot_de_passe'])
        passager.save()
        Reservation.objects.filter(telephone=passager.telephone, passager__isnull=True).update(passager=passager)
        request.session['passager_id'] = passager.id
        messages.success(request, f"Bienvenue {passager.nom_complet} ! Votre compte Supabase est créé.")
        return redirect('compte_dashboard')

    return render(request, 'reservations/compte_inscription.html', {'form': form, 'supabase': True})


def compte_connexion(request):
    if passager_connecte(request):
        return redirect('compte_dashboard')

    form = PassagerConnexionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        telephone = form.cleaned_data['telephone'].strip()
        passager = Passager.objects.filter(telephone=telephone).first()
        if passager and passager.verifier_mot_de_passe(form.cleaned_data['mot_de_passe']):
            Reservation.objects.filter(telephone=passager.telephone, passager__isnull=True).update(passager=passager)
            request.session['passager_id'] = passager.id
            return redirect('compte_dashboard')
        messages.error(request, "Téléphone ou mot de passe incorrect.")

    return render(request, 'reservations/compte_connexion.html', {'form': form})


def compte_connexion_supabase(request):
    """Connexion passager via Supabase Auth (email + mot de passe)."""
    if passager_connecte(request):
        return redirect('compte_dashboard')

    form = PassagerConnexionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        telephone = form.cleaned_data['telephone'].strip()
        email = request.POST.get('email', '')
        mot_de_passe = form.cleaned_data['mot_de_passe']

        identifiant = email or f"{telephone}@passager.silimu"
        response, error = supabase_sign_in(identifiant, mot_de_passe)
        if error:
            messages.error(request, "Identifiants Supabase incorrects.")
            return render(request, 'reservations/compte_connexion.html', {'form': form})

        passager = Passager.objects.filter(telephone=telephone).first()
        if passager:
            Reservation.objects.filter(telephone=passager.telephone, passager__isnull=True).update(passager=passager)
            request.session['passager_id'] = passager.id
            request.session['supabase_token'] = response.session.access_token if hasattr(response, 'session') else None
            return redirect('compte_dashboard')

        messages.error(request, "Aucun compte passager trouvé.")
        return render(request, 'reservations/compte_connexion.html', {'form': form})

    return render(request, 'reservations/compte_connexion.html', {'form': form, 'supabase': True})


def compte_deconnexion(request):
    supabase_token = request.session.pop('supabase_token', None)
    if supabase_token:
        supabase_sign_out(supabase_token)
    request.session.pop('passager_id', None)
    return redirect('home')


@passager_required
def compte_dashboard(request):
    passager = passager_connecte(request)
    reservations = passager.reservations.select_related(
        'traversee', 'traversee__route', 'traversee__bateau'
    ).order_by('-date_creation')
    return render(request, 'reservations/compte_dashboard.html', {
        'passager': passager,
        'reservations': reservations,
    })


# ---------------------------------------------------------------------
# Authentification back-office
# ---------------------------------------------------------------------

def admin_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard' if est_administrateur(request.user) else 'admin_comptoir')

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        if not user.is_staff:
            messages.error(request, "Ce compte n'a pas accès au back-office.")
        else:
            login(request, user)
            return redirect('admin_dashboard' if est_administrateur(user) else 'admin_comptoir')

    return render(request, 'reservations/admin_login.html', {'form': form})


def admin_logout(request):
    logout(request)
    return redirect('home')


# ---------------------------------------------------------------------
# Back-office — vente au comptoir (agents guichet + administrateurs)
# ---------------------------------------------------------------------

@agent_required
def admin_comptoir(request):
    traversee = None
    traversee_id = request.GET.get('traversee') or request.POST.get('traversee')
    if traversee_id:
        traversee = get_object_or_404(Traversee.objects.select_related('route', 'bateau'), pk=traversee_id)

    if request.method == 'POST' and traversee:
        form = ReservationComptoirForm(request.POST, traversee=traversee)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.traversee = traversee
            reservation.total = Decimal(reservation.nb_places) * traversee.prix
            reservation.mode_paiement = Reservation.ModePaiement.ESPECES
            reservation.statut = Reservation.Statut.CONFIRME  # encaissé sur place, immédiatement confirmé
            reservation.enregistre_par = request.user
            reservation.save()
            _finaliser_si_payee(reservation)
            messages.success(request, f"Billet {reservation.code} enregistré et payé en espèces.")
            return redirect('billet', code=reservation.code)
    else:
        form = ReservationComptoirForm(traversee=traversee) if traversee else None

    traversees_du_jour = Traversee.objects.select_related('route', 'bateau').filter(
        date__gte=timezone.localdate(), bateau__en_service=True
    ).order_by('date', 'heure')[:100]

    return render(request, 'reservations/admin_comptoir.html', {
        'form': form,
        'traversee': traversee,
        'traversees_du_jour': traversees_du_jour,
    })


# ---------------------------------------------------------------------
# Back-office — statistiques (administrateurs uniquement)
# ---------------------------------------------------------------------

@admin_required
def admin_dashboard(request):
    payees = Reservation.objects.filter(statut=Reservation.Statut.CONFIRME)

    par_ligne = (
        payees.values('traversee__route__port_depart', 'traversee__route__port_arrivee')
        .annotate(recette=Sum('total'), places=Sum('nb_places'))
        .order_by('-recette')
    )
    par_bateau = (
        payees.values('traversee__bateau__nom')
        .annotate(recette=Sum('total'), places=Sum('nb_places'))
        .order_by('-recette')
    )
    par_mode = (
        payees.values('mode_paiement')
        .annotate(nb_transactions=Count('id'), recette=Sum('total'))
        .order_by('-recette')
    )
    for m in par_mode:
        m['mode_paiement'] = Reservation.ModePaiement(m['mode_paiement']).label

    stats = {
        'reservations_actives': payees.count(),
        'recette_totale': payees.aggregate(total=Sum('total'))['total'] or 0,
        'places_vendues': payees.aggregate(total=Sum('nb_places'))['total'] or 0,
        'en_attente': Reservation.objects.filter(statut=Reservation.Statut.EN_ATTENTE).count(),
        'traversees_aujourdhui': Traversee.objects.filter(date=timezone.localdate()).count(),
        'nb_lignes': Route.objects.count(),
        'nb_bateaux': Bateau.objects.count(),
        'nb_bateaux_maintenance': Bateau.objects.filter(en_service=False).count(),
        'nb_traversees': Traversee.objects.count(),
    }

    traversees_a_venir = Traversee.objects.select_related('route', 'bateau').filter(
        date__gte=timezone.localdate()
    ).order_by('date', 'heure')[:30]
    taux_moyen = 0
    liste_taux = [t.taux_remplissage() for t in traversees_a_venir if t.bateau.capacite]
    if liste_taux:
        taux_moyen = round(sum(liste_taux) / len(liste_taux))

    return render(request, 'reservations/admin_dashboard.html', {
        'stats': stats,
        'par_ligne': list(par_ligne),
        'par_bateau': list(par_bateau),
        'par_mode': list(par_mode),
        'taux_moyen': taux_moyen,
    })


# ---------------------------------------------------------------------
# Back-office — Lignes (administrateurs uniquement)
# ---------------------------------------------------------------------

@admin_required
def admin_routes(request):
    if request.method == 'POST':
        form = RouteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Ligne ajoutée.")
            return redirect('admin_routes')
    else:
        form = RouteForm()
    routes = Route.objects.all()
    return render(request, 'reservations/admin_routes.html', {'form': form, 'routes': routes})


@admin_required
def admin_route_delete(request, pk):
    route = get_object_or_404(Route, pk=pk)
    route.delete()
    messages.success(request, "Ligne supprimée.")
    return redirect('admin_routes')


# ---------------------------------------------------------------------
# Back-office — Bateaux (administrateurs uniquement)
# ---------------------------------------------------------------------

@admin_required
def admin_boats(request):
    if request.method == 'POST':
        form = BateauForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Bateau ajouté.")
            return redirect('admin_boats')
    else:
        form = BateauForm()
    bateaux = Bateau.objects.all()
    return render(request, 'reservations/admin_boats.html', {'form': form, 'bateaux': bateaux})


@admin_required
def admin_boat_delete(request, pk):
    bateau = get_object_or_404(Bateau, pk=pk)
    bateau.delete()
    messages.success(request, "Bateau supprimé.")
    return redirect('admin_boats')


@admin_required
@require_POST
def admin_boat_toggle_service(request, pk):
    """Basculer un bateau en maintenance / remise en service."""
    bateau = get_object_or_404(Bateau, pk=pk)
    bateau.en_service = not bateau.en_service
    bateau.save(update_fields=['en_service'])
    etat = "remis en service" if bateau.en_service else "mis en maintenance"
    messages.success(request, f"{bateau.nom} {etat}.")
    return redirect('admin_boats')


# ---------------------------------------------------------------------
# Back-office — Traversées (administrateurs uniquement)
# ---------------------------------------------------------------------

@admin_required
def admin_trips(request):
    if request.method == 'POST':
        form = TraverseeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Traversée programmée.")
            return redirect('admin_trips')
    else:
        form = TraverseeForm()
    traversees = Traversee.objects.select_related('route', 'bateau').order_by('date', 'heure')
    return render(request, 'reservations/admin_trips.html', {'form': form, 'traversees': traversees})


@admin_required
def admin_trip_delete(request, pk):
    traversee = get_object_or_404(Traversee, pk=pk)
    traversee.delete()
    messages.success(request, "Traversée supprimée.")
    return redirect('admin_trips')


# ---------------------------------------------------------------------
# Back-office — Réservations (agents guichet + administrateurs)
# ---------------------------------------------------------------------

@agent_required
def admin_bookings(request):
    reservations = Reservation.objects.select_related(
        'traversee', 'traversee__route', 'traversee__bateau'
    ).order_by('-date_creation')
    return render(request, 'reservations/admin_bookings.html', {'reservations': reservations})


@agent_required
def admin_booking_confirm(request, pk):
    """Encaissement d'une réservation EN ATTENTE (espèces payées au guichet).
    Le passage à CONFIRME libère automatiquement l'envoi du billet par e-mail."""
    reservation = get_object_or_404(Reservation, pk=pk)
    if reservation.statut == Reservation.Statut.EN_ATTENTE:
        reservation.marquer_payee()
        _finaliser_si_payee(reservation)
        messages.success(
            request,
            f"Réservation {reservation.code} encaissée : le billet a été envoyé à {reservation.email or reservation.telephone}.",
        )
    else:
        messages.warning(
            request,
            "Seules les réservations « En attente de paiement » peuvent être encaissées au comptoir.",
        )
    return redirect('admin_bookings')


@agent_required
def admin_booking_cancel(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)
    reservation.statut = Reservation.Statut.ANNULE
    reservation.save()
    from .notifications import envoyer_annulation_email
    envoyer_annulation_email(reservation)
    messages.success(request, f"Réservation {reservation.code} annulée.")
    return redirect('admin_bookings')


# ---------------------------------------------------------------------
# Back-office — Exports comptables (administrateurs uniquement)
# ---------------------------------------------------------------------

def _reservations_pour_export():
    return Reservation.objects.select_related(
        'traversee', 'traversee__route', 'traversee__bateau'
    ).order_by('-date_creation')


@admin_required
def export_bookings_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="reservations_silimu.csv"'
    writer = csv.writer(response)
    writer.writerow(['Code', 'Passager', 'Téléphone', 'Ligne', 'Date', 'Heure', 'Bateau',
                      'Places', 'Total (FC)', 'Mode de paiement', 'Statut', 'Créé le'])
    for r in _reservations_pour_export():
        writer.writerow([
            r.code, r.nom_passager, r.telephone, str(r.traversee.route),
            r.traversee.date, r.traversee.heure, r.traversee.bateau.nom,
            r.nb_places, r.total, r.get_mode_paiement_display(), r.get_statut_display(),
            r.date_creation.strftime('%Y-%m-%d %H:%M'),
        ])
    return response


@admin_required
def export_bookings_xlsx(request):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Réservations SILIMU"
    entetes = ['Code', 'Passager', 'Téléphone', 'Ligne', 'Date', 'Heure', 'Bateau',
               'Places', 'Total (FC)', 'Mode de paiement', 'Statut', 'Créé le']
    ws.append(entetes)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for r in _reservations_pour_export():
        ws.append([
            r.code, r.nom_passager, r.telephone, str(r.traversee.route),
            r.traversee.date.strftime('%Y-%m-%d'), r.traversee.heure.strftime('%H:%M'),
            r.traversee.bateau.nom, r.nb_places, float(r.total),
            r.get_mode_paiement_display(), r.get_statut_display(),
            r.date_creation.strftime('%Y-%m-%d %H:%M'),
        ])

    for col in ws.columns:
        largeur = max(len(str(c.value)) if c.value else 0 for c in col) + 2
        ws.column_dimensions[col[0].column_letter].width = min(largeur, 40)

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="reservations_silimu.xlsx"'
    return response


@admin_required
def export_bookings_pdf(request):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), title="Réservations SILIMU")
    styles = getSampleStyleSheet()

    data = [['Code', 'Passager', 'Téléphone', 'Ligne', 'Date', 'Places', 'Total (FC)', 'Paiement', 'Statut']]
    for r in _reservations_pour_export():
        data.append([
            r.code, r.nom_passager, r.telephone, str(r.traversee.route),
            r.traversee.date.strftime('%d/%m/%Y'), str(r.nb_places),
            f"{r.total:,.0f}".replace(',', ' '), r.get_mode_paiement_display(), r.get_statut_display(),
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0B3D4C')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F6F1E4')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    titre = Paragraph("Réservations — SILIMU (transport lacustre)", styles['Title'])
    doc.build([titre, table])
    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reservations_silimu.pdf"'
    return response
