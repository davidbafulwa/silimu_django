"""
Points d'entrée de l'API REST — utilisables par une future application
mobile native (ou tout autre client) sans passer par les pages HTML.
Lecture publique ; création de réservation publique (paiement Mobile
Money à initier ensuite côté client via le flux CinetPay classique).
"""
from rest_framework import viewsets, mixins
from rest_framework.permissions import AllowAny

from .models import Route, Bateau, Traversee, Reservation
from .serializers import (
    RouteSerializer, BateauSerializer, TraverseeSerializer,
    ReservationCreateSerializer, ReservationReadSerializer,
)


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    permission_classes = [AllowAny]


class BateauViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Bateau.objects.filter(en_service=True)
    serializer_class = BateauSerializer
    permission_classes = [AllowAny]


class TraverseeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TraverseeSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Traversee.objects.select_related('route', 'bateau').filter(bateau__en_service=True)
        params = self.request.query_params
        if params.get('route'):
            qs = qs.filter(route_id=params['route'])
        if params.get('bateau'):
            qs = qs.filter(bateau_id=params['bateau'])
        if params.get('date'):
            qs = qs.filter(date=params['date'])
        return qs.order_by('date', 'heure')


class ReservationViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    POST /api/reservations/         -> créer une réservation (statut "en attente")
    GET  /api/reservations/<code>/  -> consulter un billet par son code
    """
    queryset = Reservation.objects.select_related('traversee', 'traversee__route', 'traversee__bateau')
    permission_classes = [AllowAny]
    lookup_field = 'code'

    def get_serializer_class(self):
        if self.action == 'create':
            return ReservationCreateSerializer
        return ReservationReadSerializer
