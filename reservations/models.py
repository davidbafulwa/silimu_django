import random
import string

from django.db import models
from django.db.models import Sum
from django.core.validators import MinValueValidator
from django.contrib.auth.hashers import make_password, check_password


def generer_code():
    """Génère un code de billet unique lisible, ex: SLM-KTQP-4821."""
    lettres = ''.join(random.choices(string.ascii_uppercase, k=4))
    chiffres = ''.join(random.choices(string.digits, k=4))
    return f"SLM-{lettres}-{chiffres}"


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


class Route(models.Model):
    """Une ligne lacustre reliant deux ports (ex: Munyaga -> Kasenyi)."""
    port_depart = models.CharField("Port de départ", max_length=80)
    port_arrivee = models.CharField("Port d'arrivée", max_length=80)
    distance_km = models.PositiveIntegerField("Distance (km)")
    duree_min = models.PositiveIntegerField("Durée du trajet (minutes)")

    class Meta:
        verbose_name = "Ligne"
        verbose_name_plural = "Lignes"
        ordering = ['port_depart', 'port_arrivee']
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
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='traversees', verbose_name="Ligne")
    bateau = models.ForeignKey(Bateau, on_delete=models.CASCADE, related_name='traversees', verbose_name="Bateau")
    date = models.DateField("Date")
    heure = models.TimeField("Heure de départ")
    prix = models.DecimalField("Prix unitaire (FC)", max_digits=10, decimal_places=2)
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
    date_creation = models.DateTimeField("Créé le", auto_now_add=True)

    def marquer_payee(self):
        self.statut = Reservation.Statut.CONFIRME
        self.save(update_fields=['statut'])

    def marquer_echec(self):
        self.statut = Reservation.Statut.ECHEC
        self.save(update_fields=['statut'])

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
        super().save(*args, **kwargs)

    @classmethod
    def nom_pour_telephone(cls, telephone):
        """Retourne le nom du dernier passager connu pour ce numéro (historique des passagers)."""
        if not telephone:
            return None
        dernier = cls.objects.filter(telephone=telephone).order_by('-date_creation').first()
        return dernier.nom_passager if dernier else None
