from django.contrib import admin
from .models import (
    Port, Route, Bateau, Traversee, Reservation, Passager,
    Embarquement, Remboursement, HistoriqueReservation,
    RecompenseFidelite, NotificationInterne,
)


@admin.register(Passager)
class PassagerAdmin(admin.ModelAdmin):
    list_display = ('nom_complet', 'telephone', 'email', 'date_inscription')
    search_fields = ('nom_complet', 'telephone', 'email')
    readonly_fields = ('mot_de_passe', 'date_inscription')


@admin.register(Port)
class PortAdmin(admin.ModelAdmin):
    list_display = ('nom', 'ville', 'telephone', 'est_actif')
    list_filter = ('est_actif', 'ville')
    search_fields = ('nom', 'ville')


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('port_depart', 'port_arrivee', 'distance_km', 'duree_min')
    search_fields = ('port_depart__nom', 'port_arrivee__nom')


@admin.register(Bateau)
class BateauAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type_bateau', 'capacite', 'en_service')
    list_filter = ('type_bateau', 'en_service')


@admin.register(Traversee)
class TraverseeAdmin(admin.ModelAdmin):
    list_display = ('route', 'bateau', 'date', 'heure', 'prix', 'statut', 'places_reservees', 'places_disponibles', 'taux_remplissage')
    list_filter = ('date', 'route', 'bateau', 'statut')
    date_hierarchy = 'date'


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom_passager', 'telephone', 'email', 'traversee', 'nb_places',
                     'total', 'mode_paiement', 'statut', 'enregistre_par', 'date_creation')
    list_filter = ('statut', 'mode_paiement', 'archivee')
    search_fields = ('code', 'nom_passager', 'telephone', 'email')
    readonly_fields = ('code', 'date_creation', 'billet_envoye', 'expire_le')
    actions = ['archiver_et_supprimer']

    def get_queryset(self, request):
        return super().get_queryset(request).filter(archivee=False)

    @admin.action(description="🗄 Archiver dans l'historique (masquer pour l'admin)")
    def archiver_et_supprimer(self, request, queryset):
        """Copie chaque réservation dans l'historique puis la masque de
        la liste active : l'admin ne voit plus l'ancien billet, mais le
        passager avec un compte conserve l'accès."""
        n = 0
        for reservation in queryset.select_related('traversee', 'embarquement__valide_par'):
            HistoriqueReservation.creer_depuis(reservation, archive_par=request.user)
            reservation.archivee = True
            reservation.save(update_fields=['archivee'])
            n += 1
        self.message_user(
            request,
            f"{n} réservation(s) archivée(s) : masquée(s) de la liste admin, l'historique est conservé.",
        )


@admin.register(Embarquement)
class EmbarquementAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'traversee', 'date_embarquement', 'valide_par')
    list_filter = ('traversee',)
    search_fields = ('reservation__code', 'reservation__nom_passager')


@admin.register(Remboursement)
class RemboursementAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'montant', 'motif', 'cree_par', 'date_creation')
    list_filter = ('motif',)
    search_fields = ('reservation__code', 'reservation__nom_passager')


@admin.register(HistoriqueReservation)
class HistoriqueReservationAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom_passager', 'statut', 'traversee', 'date_creation',
                    'embarquement_le', 'rembourse_total', 'archive_le', 'archive_par')
    list_filter = ('statut', 'mode_paiement', 'archive_le')
    search_fields = ('code', 'nom_passager', 'telephone', 'email')
    date_hierarchy = 'archive_le'
    readonly_fields = [f.name for f in HistoriqueReservation._meta.fields]
    list_max_show_all = 500
    list_per_page = 100

    def has_add_permission(self, request):
        return False


@admin.register(RecompenseFidelite)
class RecompenseFideliteAdmin(admin.ModelAdmin):
    list_display = ('code', 'telephone', 'email', 'seuil', 'utilisee', 'envoye_le', 'cree_le')
    list_filter = ('seuil', 'utilisee')
    search_fields = ('code', 'telephone', 'email')
    readonly_fields = ('code', 'cree_le', 'envoye_le')
    ordering = ('-cree_le',)


@admin.register(NotificationInterne)
class NotificationInterneAdmin(admin.ModelAdmin):
    list_display = ('type', 'message', 'telephone', 'lue', 'cree_le')
    list_filter = ('type', 'lue')
    search_fields = ('message', 'telephone')
    readonly_fields = ('cree_le',)
    ordering = ('-cree_le',)