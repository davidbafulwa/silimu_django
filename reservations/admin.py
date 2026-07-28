from django.contrib import admin
from .models import Route, Bateau, Traversee, Reservation, Passager


@admin.register(Passager)
class PassagerAdmin(admin.ModelAdmin):
    list_display = ('nom_complet', 'telephone', 'email', 'date_inscription')
    search_fields = ('nom_complet', 'telephone', 'email')
    readonly_fields = ('mot_de_passe', 'date_inscription')


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('port_depart', 'port_arrivee', 'distance_km', 'duree_min')
    search_fields = ('port_depart', 'port_arrivee')


@admin.register(Bateau)
class BateauAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type_bateau', 'capacite', 'en_service')
    list_filter = ('type_bateau', 'en_service')


@admin.register(Traversee)
class TraverseeAdmin(admin.ModelAdmin):
    list_display = ('route', 'bateau', 'date', 'heure', 'prix', 'places_reservees', 'places_disponibles', 'taux_remplissage')
    list_filter = ('date', 'route', 'bateau')
    date_hierarchy = 'date'


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom_passager', 'telephone', 'email', 'traversee', 'nb_places',
                     'total', 'mode_paiement', 'statut', 'enregistre_par', 'date_creation')
    list_filter = ('statut', 'mode_paiement')
    search_fields = ('code', 'nom_passager', 'telephone', 'email')
    readonly_fields = ('code', 'date_creation', 'billet_envoye')
