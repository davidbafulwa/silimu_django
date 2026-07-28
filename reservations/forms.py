from django import forms
from .models import Route, Bateau, Traversee, Reservation, Passager


class PassagerInscriptionForm(forms.Form):
    nom_complet = forms.CharField(label="Nom complet", max_length=120)
    telephone = forms.CharField(label="Téléphone", max_length=30)
    email = forms.EmailField(label="E-mail (facultatif)", required=False)
    mot_de_passe = forms.CharField(label="Mot de passe", widget=forms.PasswordInput, min_length=6)
    mot_de_passe_confirmation = forms.CharField(label="Confirmer le mot de passe", widget=forms.PasswordInput)

    def clean_telephone(self):
        telephone = self.cleaned_data['telephone'].strip()
        if Passager.objects.filter(telephone=telephone).exists():
            raise forms.ValidationError("Un compte existe déjà avec ce numéro de téléphone.")
        return telephone

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('mot_de_passe') and cleaned.get('mot_de_passe_confirmation'):
            if cleaned['mot_de_passe'] != cleaned['mot_de_passe_confirmation']:
                raise forms.ValidationError("Les deux mots de passe ne correspondent pas.")
        return cleaned


class PassagerConnexionForm(forms.Form):
    telephone = forms.CharField(label="Téléphone")
    mot_de_passe = forms.CharField(label="Mot de passe", widget=forms.PasswordInput)


class RechercheForm(forms.Form):
    depart = forms.CharField(label="Départ", required=False)
    arrivee = forms.CharField(label="Arrivée", required=False)
    date = forms.DateField(label="Date", required=False, widget=forms.DateInput(attrs={'type': 'date'}))


class ReservationForm(forms.ModelForm):
    """Formulaire de réservation en ligne (paiement Mobile Money / carte uniquement)."""

    class Meta:
        model = Reservation
        fields = ['nom_passager', 'telephone', 'email', 'nb_places', 'mode_paiement']
        labels = {
            'nom_passager': 'Nom complet du passager',
            'telephone': 'Téléphone (Mobile Money)',
            'email': 'E-mail (facultatif, pour recevoir le billet)',
            'nb_places': 'Nombre de places',
            'mode_paiement': 'Mode de paiement',
        }
        widgets = {
            'nb_places': forms.NumberInput(attrs={'min': 1}),
            'telephone': forms.TextInput(attrs={'id': 'id_telephone'}),
            'nom_passager': forms.TextInput(attrs={'id': 'id_nom_passager'}),
        }

    def __init__(self, *args, traversee=None, **kwargs):
        self.traversee = traversee
        super().__init__(*args, **kwargs)
        # Le paiement en ligne exclut le règlement en espèces (réservé au comptoir)
        self.fields['mode_paiement'].choices = [
            c for c in Reservation.ModePaiement.choices if c[0] != Reservation.ModePaiement.ESPECES
        ]

    def clean_nb_places(self):
        nb_places = self.cleaned_data['nb_places']
        if self.traversee and nb_places > self.traversee.places_disponibles():
            raise forms.ValidationError(
                f"Il ne reste que {self.traversee.places_disponibles()} place(s) disponible(s) sur cette traversée."
            )
        return nb_places


class ReservationComptoirForm(forms.ModelForm):
    """Formulaire utilisé par les agents guichet pour une vente au comptoir (espèces)."""

    class Meta:
        model = Reservation
        fields = ['nom_passager', 'telephone', 'email', 'nb_places']
        labels = {
            'nom_passager': 'Nom complet du passager',
            'telephone': 'Téléphone',
            'email': 'E-mail (facultatif, pour lui envoyer le billet)',
            'nb_places': 'Nombre de places',
        }
        widgets = {
            'nb_places': forms.NumberInput(attrs={'min': 1}),
        }

    def __init__(self, *args, traversee=None, **kwargs):
        self.traversee = traversee
        super().__init__(*args, **kwargs)

    def clean_nb_places(self):
        nb_places = self.cleaned_data['nb_places']
        if self.traversee and nb_places > self.traversee.places_disponibles():
            raise forms.ValidationError(
                f"Il ne reste que {self.traversee.places_disponibles()} place(s) disponible(s) sur cette traversée."
            )
        return nb_places


class MesBilletsForm(forms.Form):
    q = forms.CharField(label="Code ou téléphone", required=True)


class RouteForm(forms.ModelForm):
    class Meta:
        model = Route
        fields = ['port_depart', 'port_arrivee', 'distance_km', 'duree_min']


class BateauForm(forms.ModelForm):
    class Meta:
        model = Bateau
        fields = ['nom', 'capacite', 'type_bateau', 'en_service']


class TraverseeForm(forms.ModelForm):
    class Meta:
        model = Traversee
        fields = ['route', 'bateau', 'date', 'heure', 'prix']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'heure': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Un bateau en maintenance (hors service) ne doit pas pouvoir être programmé
        self.fields['bateau'].queryset = Bateau.objects.filter(en_service=True)
