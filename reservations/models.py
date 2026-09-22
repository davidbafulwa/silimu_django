import random
import string

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.core.validators import MinValueValidator
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import timedelta


def generer_code():
    """Génère un code de billet unique lisible, ex: SLM-KTQP-4821."""
    lettres = ''.join(random.choices(string.ascii_uppercase, k=4))
    chiffres = ''.join(random.choices(string.digits, k=4))
    return f"SLM-{lettres}-{chiffres}"


def generer_code_fidelite():
    """Génère un code de récompense unique, ex: FID-7K2M9Q."""
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    return 'FID-' + ''.join(random.choice(alphabet) for _ in range(6))


class Passager(models.Model):
    """Compte client permettant à un passager de retrouver son historique
    de réservations sans ressaisir son téléphone à chaque fois."""
    nom_complet = models.CharField("Nom complet", max_length=120)
    telephone = models.CharField("Téléphone", max_length=30, unique=True)
    email = models.EmailField("E-mail", blank=True)
    mot_de_passe = models.CharField("Mot de passe (haché)", max_length=128)
    date_inscription = models.DateTimeField("Inscrit le", auto_now_add=True)

    class Meta:
        verbose_name = "Passager (compte)"
        verbose_name_plural = "Passagers (comptes)"
        ordering = ['-date_inscription']

    def __str__(self):
        return f"{self.nom_complet} ({self.telephone})"

    def definir_mot_de_passe(self, mot_de_passe_clair):
        self.mot_de_passe = make_password(mot_de_passe_clair)

    def verifier_mot_de_passe(self, mot_de_passe_clair):
        return check_password(mot_de_passe_clair, self.mot_de_passe)


class Port(models.Model):
    """Un port / point d'embarquement sur le lac (entité à part entière)."""
    nom = models.CharField("Nom du port", max_length=80, unique=True)
    ville = models.CharField("Ville", max_length=80, blank=True)
    coordonnees_gps = models.CharField("Coordonnées GPS", max_length=80, blank=True, help_text="Ex: -2.50, 28.86")
    telephone = models.CharField("Téléphone", max_length=30, blank=True)
    est_actif = models.BooleanField("Actif", default=True)

    class Meta:
        verbose_name = "Port"
        verbose_name_plural = "Ports"
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Route(models.Model):
    """Une ligne lacustre reliant deux ports (ex: Munyaga -> Kasenyi)."""
    port_depart = models.ForeignKey(
        Port, on_delete=models.CASCADE, related_name='routes_depart', verbose_name="Port de départ"
    )
    port_arrivee = models.ForeignKey(
        Port, on_delete=models.CASCADE, related_name='routes_arrivee', verbose_name="Port d'arrivée"
    )
    distance_km = models.PositiveIntegerField("Distance (km)")
    duree_min = models.PositiveIntegerField("Durée du trajet (minutes)")

    class Meta:
        verbose_name = "Ligne"
        verbose_name_plural = "Lignes"
        ordering = ['port_depart__nom', 'port_arrivee__nom']
        constraints = [
            models.UniqueConstraint(
                fields=['port_depart', 'port_arrivee'],
                name='ligne_unique_depart_arrivee'
            )
        ]

    def __str__(self):
        return f"{self.port_depart} → {self.port_arrivee}"


class Bateau(models.Model):
    """Une unité navale exploitée par SILIMU."""

    class TypeBateau(models.TextChoices):
        VEDETTE = 'VEDETTE', 'Vedette rapide'
        FERRY = 'FERRY', 'Ferry'
        PIROGUE = 'PIROGUE', 'Pirogue motorisée'

    nom = models.CharField("Nom du bateau", max_length=100, unique=True)
    capacite = models.PositiveIntegerField("Capacité (places)", validators=[MinValueValidator(1)])
    type_bateau = models.CharField(
        "Type", max_length=20, choices=TypeBateau.choices, default=TypeBateau.VEDETTE
    )
    en_service = models.BooleanField("En service", default=True)

    class Meta:
        verbose_name = "Bateau"
        verbose_name_plural = "Bateaux"
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Traversee(models.Model):
    """Une traversée programmée : une ligne + un bateau, à une date/heure et un prix donnés."""

    class Statut(models.TextChoices):
        PROGRAMMEE = 'PROGRAMMEE', 'Programmée'
        RETARDEE = 'RETARDEE', 'Retardée'
        PARTIE = 'PARTIE', 'Partie'
        ANNULEE = 'ANNULEE', 'Annulée'

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='traversees', verbose_name="Ligne")
    bateau = models.ForeignKey(Bateau, on_delete=models.CASCADE, related_name='traversees', verbose_name="Bateau")
    date = models.DateField("Date")
    heure = models.TimeField("Heure de départ")
    prix = models.DecimalField("Prix unitaire (FC)", max_digits=10, decimal_places=2)
    statut = models.CharField("Statut", max_length=12, choices=Statut.choices, default=Statut.PROGRAMMEE)
    alerte_remplissage_envoyee = models.BooleanField(
        "Alerte de remplissage déjà envoyée", default=False, editable=False
    )

    class Meta:
        verbose_name = "Traversée"
        verbose_name_plural = "Traversées"
        ordering = ['date', 'heure']
        constraints = [
            models.UniqueConstraint(
                fields=['route', 'bateau', 'date', 'heure'],
                name='traversee_unique'
            )
        ]

    def __str__(self):
        return f"{self.route} — {self.date} {self.heure}"

    def est_disponible(self):
        """Une traversée peut être réservée si elle est programmée et que son bateau est en service."""
        return self.statut == Traversee.Statut.PROGRAMMEE and self.bateau.en_service

    def est_annulee(self):
        return self.statut == Traversee.Statut.ANNULEE

    def places_reservees(self):
        total = self.reservations.exclude(
            statut__in=[Reservation.Statut.ANNULE, Reservation.Statut.ECHEC]
        ).aggregate(total=Sum('nb_places'))['total']
        return total or 0

    def places_disponibles(self):
        return self.bateau.capacite - self.places_reservees()

    def est_complet(self):
        return self.places_disponibles() <= 0

    def taux_remplissage(self):
        if not self.bateau.capacite:
            return 0
        return round(self.places_reservees() / self.bateau.capacite * 100)

    def date_heure_depart(self):
        """Datetime "aware" du départ, utilisée pour calculer les rappels."""
        from datetime import datetime
        from django.utils import timezone
        naive = datetime.combine(self.date, self.heure)
        return timezone.make_aware(naive) if timezone.is_naive(naive) else naive


class Reservation(models.Model):
    """Un billet réservé par un passager pour une traversée donnée."""

    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente de paiement'
        CONFIRME = 'CONFIRME', 'Confirmé'
        ECHEC = 'ECHEC', 'Paiement échoué'
        ANNULE = 'ANNULE', 'Annulé'
        EMBARQUE = 'EMBARQUE', 'Embarqué'

    class ModePaiement(models.TextChoices):
        ORANGE_MONEY = 'ORANGE_MONEY', 'Orange Money'
        AIRTEL_MONEY = 'AIRTEL_MONEY', 'Airtel Money'
        MPESA = 'MPESA', 'M-Pesa'
        CARTE = 'CARTE', 'Carte bancaire'
        ESPECES = 'ESPECES', 'Espèces (comptoir)'

    traversee = models.ForeignKey(
        Traversee, on_delete=models.CASCADE, related_name='reservations', verbose_name="Traversée"
    )
    passager = models.ForeignKey(
        Passager, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reservations', verbose_name="Compte passager"
    )
    code = models.CharField("Code du billet", max_length=20, unique=True, editable=False)
    nom_passager = models.CharField("Nom du passager", max_length=120)
    telephone = models.CharField("Téléphone", max_length=30)
    email = models.EmailField("E-mail (pour recevoir le billet)", blank=True)
    nb_places = models.PositiveIntegerField("Nombre de places", validators=[MinValueValidator(1)])
    total = models.DecimalField("Total payé (FC)", max_digits=10, decimal_places=2)
    mode_paiement = models.CharField(
        "Mode de paiement", max_length=20, choices=ModePaiement.choices, default=ModePaiement.ORANGE_MONEY
    )
    statut = models.CharField("Statut", max_length=12, choices=Statut.choices, default=Statut.EN_ATTENTE)
    enregistre_par = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reservations_comptoir', verbose_name="Enregistré par (agent guichet)"
    )
    billet_envoye = models.BooleanField("Billet envoyé par e-mail", default=False, editable=False)
    rappel_envoye = models.BooleanField("Rappel de départ envoyé", default=False, editable=False)
    expire_le = models.DateTimeField("Paiement à effectuer avant", null=True, blank=True, editable=False)
    date_creation = models.DateTimeField("Créé le", auto_now_add=True)
    archivee = models.BooleanField(
        "Archivée (cachée de l'admin)", default=False, db_index=True,
        help_text="Masquée de la liste Django admin, mais le passager garde accès à son billet.",
    )

    def marquer_payee(self):
        self.statut = Reservation.Statut.CONFIRME
        self.expire_le = None
        self.save(update_fields=['statut', 'expire_le'])

    def marquer_echec(self):
        self.statut = Reservation.Statut.ECHEC
        self.expire_le = None
        self.save(update_fields=['statut', 'expire_le'])

    def est_expiree(self):
        """Vrai si c'est une attente de paiement dont le délai est dépassé."""
        return (
            self.statut == Reservation.Statut.EN_ATTENTE
            and self.expire_le is not None
            and timezone.now() > self.expire_le
        )

    class Meta:
        verbose_name = "Réservation"
        verbose_name_plural = "Réservations"
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.code} — {self.nom_passager}"

    def save(self, *args, **kwargs):
        if not self.code:
            code = generer_code()
            while Reservation.objects.filter(code=code).exists():
                code = generer_code()
            self.code = code
        # Une réservation "en attente de paiement" doit expirer après un délai
        # configurable : au-delà, ses places doivent être libérées.
        if self.statut == Reservation.Statut.EN_ATTENTE and not self.expire_le:
            self.expire_le = timezone.now() + timedelta(minutes=settings.DELAI_EXPIRATION_ATTENTE)
        super().save(*args, **kwargs)

    @classmethod
    def nom_pour_telephone(cls, telephone):
        """Retourne le nom du dernier passager connu pour ce numéro (historique des passagers)."""
        if not telephone:
            return None
        dernier = cls.objects.filter(telephone=telephone).order_by('-date_creation').first()
        return dernier.nom_passager if dernier else None


class Embarquement(models.Model):
    """Traçabilité du check-in : qui a validé chaque billet à l'embarquement, quand."""
    reservation = models.OneToOneField(
        Reservation, on_delete=models.CASCADE, related_name='embarquement', verbose_name="Réservation"
    )
    traversee = models.ForeignKey(
        Traversee, on_delete=models.CASCADE, related_name='embarquements', verbose_name="Traversée"
    )
    date_embarquement = models.DateTimeField("Embarqué le", auto_now_add=True)
    valide_par = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Validé par"
    )

    class Meta:
        verbose_name = "Embarquement"
        verbose_name_plural = "Embarquements"
        ordering = ['-date_embarquement']

    def __str__(self):
        return f"{self.reservation.code} — {self.reservation.nom_passager}"


class Remboursement(models.Model):
    """Trace comptable d'un remboursement effectué (ou à effectuer) pour un billet."""

    class Motif(models.TextChoices):
        ANNULATION = 'ANNULATION', 'Annulation du billet'
        TRAVERSEE_ANNULEE = 'TRAVERSEE_ANNULEE', 'Traversée annulée'
        AUTRE = 'AUTRE', 'Autre motif'

    reservation = models.ForeignKey(
        Reservation, on_delete=models.CASCADE, related_name='remboursements', verbose_name="Réservation"
    )
    montant = models.DecimalField("Montant remboursé (FC)", max_digits=10, decimal_places=2)
    motif = models.CharField("Motif", max_length=25, choices=Motif.choices, default=Motif.ANNULATION)
    notes = models.TextField("Notes", blank=True)
    cree_par = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Créé par"
    )
    date_creation = models.DateTimeField("Créé le", auto_now_add=True)

    class Meta:
        verbose_name = "Remboursement"
        verbose_name_plural = "Remboursements"
        ordering = ['-date_creation']

    def __str__(self):
        return f"Remboursement {self.montant} FC — {self.reservation.code}"


class HistoriqueReservation(models.Model):
    """Copie d'une réservation archivée depuis Django admin : on la sort de la
    liste active (la réservation d'origine est supprimée) tout en gardant un
    historique consultable des anciens billets."""

    code = models.CharField("Code du billet", max_length=20)
    nom_passager = models.CharField("Nom du passager", max_length=120)
    telephone = models.CharField("Téléphone", max_length=30)
    email = models.EmailField("E-mail", blank=True)
    nb_places = models.PositiveIntegerField("Nombre de places")
    total = models.DecimalField("Total payé (FC)", max_digits=10, decimal_places=2)
    mode_paiement = models.CharField(
        "Mode de paiement", max_length=20, choices=Reservation.ModePaiement.choices
    )
    statut = models.CharField("Statut final", max_length=12, choices=Reservation.Statut.choices)
    traversee = models.ForeignKey(
        Traversee, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='historique', verbose_name="Traversée"
    )
    date_creation = models.DateTimeField("Réservé le")
    expire_le = models.DateTimeField("Paiement avant", null=True, blank=True)
    embarquement_le = models.DateTimeField("Embarqué le", null=True, blank=True)
    valide_par = models.CharField("Validé par", max_length=80, blank=True)
    rembourse_total = models.DecimalField(
        "Total remboursé (FC)", max_digits=10, decimal_places=2, default=0
    )
    archive_le = models.DateTimeField("Archivé le", auto_now_add=True)
    archive_par = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Archivé par"
    )

    class Meta:
        verbose_name = "Réservation archivée"
        verbose_name_plural = "Réservations archivées"
        ordering = ['-archive_le']

    def __str__(self):
        return f"{self.code} — {self.nom_passager}"

    @classmethod
    def creer_depuis(cls, reservation, archive_par=None):
        """Copie la réservation dans l'historique (sans la supprimer : le
        passager avec un compte garde l'accès à son billet, seul l'affichage
        Django admin la cache ensuite)."""
        embarquement = getattr(reservation, 'embarquement', None)
        return cls.objects.create(
            code=reservation.code,
            nom_passager=reservation.nom_passager,
            telephone=reservation.telephone,
            email=reservation.email,
            nb_places=reservation.nb_places,
            total=reservation.total,
            mode_paiement=reservation.mode_paiement,
            statut=reservation.statut,
            traversee=reservation.traversee,
            date_creation=reservation.date_creation,
            expire_le=reservation.expire_le,
            embarquement_le=getattr(
                embarquement, 'date_embarquement', None
            ) if embarquement is not None else None,
            valide_par=str(getattr(embarquement, 'valide_par', '') or '')
            if embarquement is not None else '',
            rembourse_total=sum(
                r.montant for r in reservation.remboursements.all()
            ) or 0,
            archive_par=archive_par,
        )


class RecompenseFidelite(models.Model):
    """Un billet gratuit gagné automatiquement par un passager fidèle :
    le voyage n°10 (puis 20, 30...) est offert, l'e-mail part tout seul et
    une notification est affichée pour l'équipe SILIMU."""

    code = models.CharField("Code de récompense", max_length=20, unique=True, editable=False)
    telephone = models.CharField("Téléphone du passager", max_length=30, db_index=True)
    email = models.EmailField("E-mail de la récompense", blank=True)
    seuil = models.PositiveIntegerField("Voyages atteints", default=10)
    cree_le = models.DateTimeField("Offert le", auto_now_add=True)
    envoye_le = models.DateTimeField("E-mail envoyé le", null=True, blank=True)
    utilisee = models.BooleanField("Récompense utilisée", default=False)
    notes = models.TextField("Notes (usage du code...)", blank=True)

    class Meta:
        verbose_name = "Récompense fidélité"
        verbose_name_plural = "Récompenses fidélité"
        ordering = ['-cree_le']
        constraints = [
            models.UniqueConstraint(
                fields=['telephone', 'seuil'], name='fidelite_unique_seuil'
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.telephone} ({self.seuil} voyages)"


class NotificationInterne(models.Model):
    """Message automatique visible par l'équipe SILIMU (back-office) :
    récompense fidélité attribuée, traversée pleine, etc."""

    class Type(models.TextChoices):
        FIDELITE = 'FIDELITE', 'Fidélité'
        SYSTEME = 'SYSTEME', 'Système'

    type = models.CharField("Type", max_length=12, choices=Type.choices, default=Type.SYSTEME)
    message = models.CharField("Message", max_length=255)
    detail = models.TextField("Détail", blank=True)
    telephone = models.CharField("Téléphone concerné", max_length=30, blank=True)
    recompense = models.ForeignKey(
        RecompenseFidelite, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Récompense liée",
    )
    lue = models.BooleanField("Lue", default=False)
    cree_le = models.DateTimeField("Créée le", auto_now_add=True)

    class Meta:
        verbose_name = "Notification interne"
        verbose_name_plural = "Notifications internes"
        ordering = ['-cree_le']

    def __str__(self):
        return f"[{self.get_type_display()}] {self.message}"
