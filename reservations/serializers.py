from rest_framework import serializers
from .models import Port, Route, Bateau, Traversee, Reservation
from .services import reserver_place, SurbookingError


class PortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Port
        fields = ['id', 'nom', 'ville', 'coordonnees_gps', 'telephone', 'est_actif']


class RouteSerializer(serializers.ModelSerializer):
    port_depart = PortSerializer(read_only=True)
    port_arrivee = PortSerializer(read_only=True)

    class Meta:
        model = Route
        fields = ['id', 'port_depart', 'port_arrivee', 'distance_km', 'duree_min']


class BateauSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bateau
        fields = ['id', 'nom', 'capacite', 'type_bateau', 'en_service']


class TraverseeSerializer(serializers.ModelSerializer):
    route = RouteSerializer(read_only=True)
    bateau = BateauSerializer(read_only=True)
    places_disponibles = serializers.SerializerMethodField()

    class Meta:
        model = Traversee
        fields = ['id', 'route', 'bateau', 'date', 'heure', 'prix', 'statut', 'places_disponibles']

    def get_places_disponibles(self, obj):
        return obj.places_disponibles()


class ReservationCreateSerializer(serializers.ModelSerializer):
    """Utilisé pour créer une réservation via l'API (ex: future application mobile).
    La création passe par le service atomique : pas de surbooking possible sous
    PostgreSQL (verrouillage de la traversée lors de l'écriture)."""

    class Meta:
        model = Reservation
        fields = ['id', 'traversee', 'code', 'nom_passager', 'telephone', 'email',
                   'nb_places', 'total', 'mode_paiement', 'statut']
        read_only_fields = ['id', 'code', 'total', 'statut']

    def validate(self, data):
        traversee = data['traversee']
        nb_places = data['nb_places']
        if not traversee.est_disponible():
            raise serializers.ValidationError("Cette traversée n'est plus disponible à la réservation.")
        if nb_places > traversee.places_disponibles():
            raise serializers.ValidationError(
                f"Il ne reste que {traversee.places_disponibles()} place(s) disponible(s) sur cette traversée."
            )
        return data

    def create(self, validated_data):
        traversee = validated_data.pop('traversee')
        nb_places = validated_data.pop('nb_places')
        try:
            return reserver_place(
                traversee, nb_places, statut=Reservation.Statut.EN_ATTENTE, **validated_data
            )
        except SurbookingError as exc:
            raise serializers.ValidationError(str(exc))


class ReservationReadSerializer(serializers.ModelSerializer):
    traversee = TraverseeSerializer(read_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'traversee', 'code', 'nom_passager', 'telephone', 'email',
                   'nb_places', 'total', 'mode_paiement', 'statut', 'date_creation']
