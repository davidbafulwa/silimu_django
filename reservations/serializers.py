from rest_framework import serializers
from .models import Route, Bateau, Traversee, Reservation


class RouteSerializer(serializers.ModelSerializer):
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
        fields = ['id', 'route', 'bateau', 'date', 'heure', 'prix', 'places_disponibles']

    def get_places_disponibles(self, obj):
        return obj.places_disponibles()


class ReservationCreateSerializer(serializers.ModelSerializer):
    """Utilisé pour créer une réservation via l'API (ex: future application mobile)."""

    class Meta:
        model = Reservation
        fields = ['id', 'traversee', 'code', 'nom_passager', 'telephone', 'email',
                   'nb_places', 'total', 'mode_paiement', 'statut']
        read_only_fields = ['id', 'code', 'total', 'statut']

    def validate(self, data):
        traversee = data['traversee']
        nb_places = data['nb_places']
        if nb_places > traversee.places_disponibles():
            raise serializers.ValidationError(
                f"Il ne reste que {traversee.places_disponibles()} place(s) disponible(s) sur cette traversée."
            )
        return data

    def create(self, validated_data):
        traversee = validated_data['traversee']
        validated_data['total'] = validated_data['nb_places'] * traversee.prix
        validated_data['statut'] = Reservation.Statut.EN_ATTENTE
        return super().create(validated_data)


class ReservationReadSerializer(serializers.ModelSerializer):
    traversee = TraverseeSerializer(read_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'traversee', 'code', 'nom_passager', 'telephone', 'email',
                   'nb_places', 'total', 'mode_paiement', 'statut', 'date_creation']
