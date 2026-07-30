from django.urls import path
from . import views

urlpatterns = [
    # Espace public
    path('', views.home, name='home'),
    path('reserver/<int:traversee_id>/', views.reserver, name='reserver'),
    path('billet/<str:code>/', views.billet, name='billet'),
    path('mes-billets/', views.mes_billets, name='mes_billets'),
    path('paiement/notification/', views.paiement_notification, name='paiement_notification'),
    path('paiement/retour/<str:code>/', views.paiement_retour, name='paiement_retour'),
    path('api/passager/<str:telephone>/', views.passager_lookup, name='passager_lookup'),

    # Compte passager
    path('compte/inscription/', views.compte_inscription, name='compte_inscription'),
    path('compte/inscription/supabase/', views.compte_inscription_supabase, name='compte_inscription_supabase'),
    path('compte/connexion/', views.compte_connexion, name='compte_connexion'),
    path('compte/connexion/supabase/', views.compte_connexion_supabase, name='compte_connexion_supabase'),
    path('compte/deconnexion/', views.compte_deconnexion, name='compte_deconnexion'),
    path('compte/', views.compte_dashboard, name='compte_dashboard'),

    # Authentification back-office
    path('admin-silimu/connexion/', views.admin_login, name='admin_login'),
    path('admin-silimu/deconnexion/', views.admin_logout, name='admin_logout'),

    # Back-office — comptoir (agents + admins)
    path('admin-silimu/comptoir/', views.admin_comptoir, name='admin_comptoir'),

    # Back-office — statistiques (admins)
    path('admin-silimu/', views.admin_dashboard, name='admin_dashboard'),

    # Back-office — lignes (admins)
    path('admin-silimu/lignes/', views.admin_routes, name='admin_routes'),
    path('admin-silimu/lignes/<int:pk>/supprimer/', views.admin_route_delete, name='admin_route_delete'),

    # Back-office — bateaux (admins)
    path('admin-silimu/bateaux/', views.admin_boats, name='admin_boats'),
    path('admin-silimu/bateaux/<int:pk>/supprimer/', views.admin_boat_delete, name='admin_boat_delete'),
    path('admin-silimu/bateaux/<int:pk>/service/', views.admin_boat_toggle_service, name='admin_boat_toggle_service'),

    # Back-office — traversées (admins)
    path('admin-silimu/traversees/', views.admin_trips, name='admin_trips'),
    path('admin-silimu/traversees/<int:pk>/supprimer/', views.admin_trip_delete, name='admin_trip_delete'),

    # Back-office — réservations (agents + admins)
    path('admin-silimu/reservations/', views.admin_bookings, name='admin_bookings'),
    path('admin-silimu/reservations/<int:pk>/annuler/', views.admin_booking_cancel, name='admin_booking_cancel'),

    # Back-office — exports comptables (admins)
    path('admin-silimu/reservations/export/csv/', views.export_bookings_csv, name='export_bookings_csv'),
    path('admin-silimu/reservations/export/xlsx/', views.export_bookings_xlsx, name='export_bookings_xlsx'),
    path('admin-silimu/reservations/export/pdf/', views.export_bookings_pdf, name='export_bookings_pdf'),
]
