from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User, Group
from django.test import TestCase, Client
from django.urls import reverse

from .decorators import GROUPE_ADMIN, GROUPE_AGENT
from .models import Route, Bateau, Traversee, Reservation, Passager


def creer_jeu_de_donnees():
    route = Route.objects.create(port_depart="Munyaga", port_arrivee="Kasenyi", distance_km=38, duree_min=75)
    bateau = Bateau.objects.create(nom="MV Test", capacite=10, type_bateau=Bateau.TypeBateau.VEDETTE)
    traversee = Traversee.objects.create(
        route=route, bateau=bateau, date=date.today() + timedelta(days=1),
        heure=time(9, 0), prix=Decimal("10000")
    )
    return route, bateau, traversee


class ModelTests(TestCase):
    def test_code_billet_unique_et_genere(self):
        _, _, traversee = creer_jeu_de_donnees()
        r1 = Reservation.objects.create(
            traversee=traversee, nom_passager="A", telephone="0900000001",
            nb_places=1, total=10000
        )
        r2 = Reservation.objects.create(
            traversee=traversee, nom_passager="B", telephone="0900000002",
            nb_places=1, total=10000
        )
        self.assertTrue(r1.code.startswith("SLM-"))
        self.assertNotEqual(r1.code, r2.code)

    def test_places_disponibles_exclut_echec_et_annule(self):
        _, bateau, traversee = creer_jeu_de_donnees()
        Reservation.objects.create(
            traversee=traversee, nom_passager="A", telephone="1", nb_places=3,
            total=30000, statut=Reservation.Statut.CONFIRME
        )
        Reservation.objects.create(
            traversee=traversee, nom_passager="B", telephone="2", nb_places=4,
            total=40000, statut=Reservation.Statut.ECHEC
        )
        Reservation.objects.create(
            traversee=traversee, nom_passager="C", telephone="3", nb_places=2,
            total=20000, statut=Reservation.Statut.ANNULE
        )
        # seules les 3 places CONFIRME comptent ; capacité 10 -> 7 restantes
        self.assertEqual(traversee.places_disponibles(), 7)

    def test_taux_remplissage(self):
        _, bateau, traversee = creer_jeu_de_donnees()
        Reservation.objects.create(
            traversee=traversee, nom_passager="A", telephone="1", nb_places=5,
            total=50000, statut=Reservation.Statut.CONFIRME
        )
        self.assertEqual(traversee.taux_remplissage(), 50)

    def test_nom_pour_telephone_historique(self):
        _, _, traversee = creer_jeu_de_donnees()
        Reservation.objects.create(
            traversee=traversee, nom_passager="Jean Kalonji", telephone="0991112222",
            nb_places=1, total=10000
        )
        self.assertEqual(Reservation.nom_pour_telephone("0991112222"), "Jean Kalonji")
        self.assertIsNone(Reservation.nom_pour_telephone("0000000000"))


class RechercheEtReservationViewTests(TestCase):
    def setUp(self):
        self.route, self.bateau, self.traversee = creer_jeu_de_donnees()
        self.client = Client()

    def test_recherche_exclut_bateau_en_maintenance(self):
        self.bateau.en_service = False
        self.bateau.save()
        response = self.client.get(reverse('home'), {'depart': 'Munyaga'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['resultats']), [])

    def test_reservation_sans_cinetpay_configure_reste_en_echec(self):
        response = self.client.post(reverse('reserver', args=[self.traversee.id]), {
            'nom_passager': 'Alice', 'telephone': '0990001111', 'email': '',
            'nb_places': 2, 'mode_paiement': 'ORANGE_MONEY',
        })
        self.assertEqual(response.status_code, 302)
        reservation = Reservation.objects.get(nom_passager='Alice')
        self.assertEqual(reservation.statut, Reservation.Statut.ECHEC)

    def test_reservation_avec_paiement_simule_confirme_et_libere_places(self):
        with patch('reservations.cinetpay.initier_paiement', return_value='https://pay.example/fake'):
            self.client.post(reverse('reserver', args=[self.traversee.id]), {
                'nom_passager': 'Bob', 'telephone': '0993334444', 'email': '',
                'nb_places': 3, 'mode_paiement': 'AIRTEL_MONEY',
            })
        reservation = Reservation.objects.get(nom_passager='Bob')
        self.assertEqual(reservation.statut, Reservation.Statut.EN_ATTENTE)

        with patch('reservations.cinetpay.verifier_paiement',
                   return_value={'code': '00', 'data': {'status': 'ACCEPTED'}}):
            self.client.post(reverse('paiement_notification'), {'cpm_trans_id': reservation.code})

        reservation.refresh_from_db()
        self.assertEqual(reservation.statut, Reservation.Statut.CONFIRME)
        self.assertEqual(self.traversee.places_disponibles(), 7)

    def test_mes_billets_recherche_par_code_et_telephone(self):
        Reservation.objects.create(
            traversee=self.traversee, nom_passager="Carla", telephone="0995556666",
            nb_places=1, total=10000, statut=Reservation.Statut.CONFIRME
        )
        r = self.client.get(reverse('mes_billets'), {'q': '0995556666'})
        self.assertEqual(len(r.context['resultats']), 1)

    def test_passager_lookup_api(self):
        Reservation.objects.create(
            traversee=self.traversee, nom_passager="Denis", telephone="0997778888",
            nb_places=1, total=10000
        )
        r = self.client.get(reverse('passager_lookup', args=['0997778888']))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['nom'], 'Denis')


class RolesEtBackOfficeTests(TestCase):
    def setUp(self):
        self.route, self.bateau, self.traversee = creer_jeu_de_donnees()
        Group.objects.get_or_create(name=GROUPE_ADMIN)
        Group.objects.get_or_create(name=GROUPE_AGENT)

        self.admin_user = User.objects.create_user('admin1', password='pass12345', is_staff=True)
        self.admin_user.groups.add(Group.objects.get(name=GROUPE_ADMIN))

        self.agent_user = User.objects.create_user('agent1', password='pass12345', is_staff=True)
        self.agent_user.groups.add(Group.objects.get(name=GROUPE_AGENT))

        self.client = Client()

    def test_non_connecte_redirige_vers_login(self):
        r = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(r.status_code, 302)

    def test_agent_ne_peut_pas_acceder_aux_statistiques(self):
        self.client.login(username='agent1', password='pass12345')
        r = self.client.get(reverse('admin_dashboard'), follow=True)
        self.assertRedirects(r, reverse('admin_comptoir'))

    def test_agent_peut_acceder_au_comptoir_et_aux_reservations(self):
        self.client.login(username='agent1', password='pass12345')
        self.assertEqual(self.client.get(reverse('admin_comptoir')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin_bookings')).status_code, 200)

    def test_admin_peut_tout_faire(self):
        self.client.login(username='admin1', password='pass12345')
        for url_name in ['admin_dashboard', 'admin_routes', 'admin_boats', 'admin_trips',
                          'admin_bookings', 'admin_comptoir']:
            self.assertEqual(self.client.get(reverse(url_name)).status_code, 200)

    def test_vente_comptoir_espece_confirme_immediatement(self):
        self.client.login(username='agent1', password='pass12345')
        r = self.client.post(
            reverse('admin_comptoir') + f'?traversee={self.traversee.id}',
            {'traversee': self.traversee.id, 'nom_passager': 'Eve', 'telephone': '0999998888',
             'email': '', 'nb_places': 2}
        )
        self.assertEqual(r.status_code, 302)
        reservation = Reservation.objects.get(nom_passager='Eve')
        self.assertEqual(reservation.statut, Reservation.Statut.CONFIRME)
        self.assertEqual(reservation.mode_paiement, Reservation.ModePaiement.ESPECES)
        self.assertEqual(reservation.enregistre_par, self.agent_user)

    def test_bateau_maintenance_exclu_du_formulaire_traversee(self):
        self.bateau.en_service = False
        self.bateau.save()
        from .forms import TraverseeForm
        form = TraverseeForm()
        self.assertNotIn(self.bateau, form.fields['bateau'].queryset)

    def test_export_csv_reserve_aux_admins(self):
        self.client.login(username='agent1', password='pass12345')
        r = self.client.get(reverse('export_bookings_csv'), follow=True)
        self.assertRedirects(r, reverse('admin_comptoir'))

        self.client.login(username='admin1', password='pass12345')
        r = self.client.get(reverse('export_bookings_csv'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'text/csv; charset=utf-8')

    def test_export_xlsx_et_pdf(self):
        self.client.login(username='admin1', password='pass12345')
        r_xlsx = self.client.get(reverse('export_bookings_xlsx'))
        self.assertEqual(r_xlsx.status_code, 200)
        r_pdf = self.client.get(reverse('export_bookings_pdf'))
        self.assertEqual(r_pdf.status_code, 200)
        self.assertEqual(r_pdf['Content-Type'], 'application/pdf')


class CompteVoyageurTests(TestCase):
    def setUp(self):
        self.route, self.bateau, self.traversee = creer_jeu_de_donnees()
        self.client = Client()

    def test_inscription_cree_compte_et_connecte(self):
        r = self.client.post(reverse('compte_inscription'), {
            'nom_complet': 'Alice Kabila', 'telephone': '0991110000', 'email': 'alice@example.com',
            'mot_de_passe': 'motdepasse123', 'mot_de_passe_confirmation': 'motdepasse123',
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Passager.objects.filter(telephone='0991110000').exists())
        r = self.client.get(reverse('compte_dashboard'))
        self.assertEqual(r.status_code, 200)

    def test_inscription_refuse_telephone_deja_utilise(self):
        Passager.objects.create(nom_complet='X', telephone='0999999999', mot_de_passe='hash')
        r = self.client.post(reverse('compte_inscription'), {
            'nom_complet': 'Y', 'telephone': '0999999999', 'email': '',
            'mot_de_passe': 'motdepasse123', 'mot_de_passe_confirmation': 'motdepasse123',
        })
        self.assertEqual(r.status_code, 200)  # reste sur le formulaire avec erreur
        self.assertEqual(Passager.objects.filter(telephone='0999999999').count(), 1)

    def test_connexion_avec_mauvais_mot_de_passe_echoue(self):
        passager = Passager(nom_complet='Bob', telephone='0992223333')
        passager.definir_mot_de_passe('bonmotdepasse')
        passager.save()
        r = self.client.post(reverse('compte_connexion'), {
            'telephone': '0992223333', 'mot_de_passe': 'mauvais',
        })
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(self.client.session.get('passager_id'))

    def test_reservations_invite_rattachees_a_la_connexion(self):
        # réservation faite en tant qu'invité, avant la création du compte
        Reservation.objects.create(
            traversee=self.traversee, nom_passager="Chris", telephone="0993334444",
            nb_places=1, total=10000, statut=Reservation.Statut.CONFIRME
        )
        passager = Passager(nom_complet='Chris', telephone='0993334444')
        passager.definir_mot_de_passe('motdepasse123')
        passager.save()
        self.client.post(reverse('compte_connexion'), {
            'telephone': '0993334444', 'mot_de_passe': 'motdepasse123',
        })
        r = self.client.get(reverse('compte_dashboard'))
        self.assertEqual(len(r.context['reservations']), 1)

    def test_reservation_en_ligne_liee_au_compte_connecte(self):
        passager = Passager(nom_complet='Dora', telephone='0994445555')
        passager.definir_mot_de_passe('motdepasse123')
        passager.save()
        self.client.post(reverse('compte_connexion'), {
            'telephone': '0994445555', 'mot_de_passe': 'motdepasse123',
        })
        self.client.post(reverse('reserver', args=[self.traversee.id]), {
            'nom_passager': 'Dora', 'telephone': '0994445555', 'email': '',
            'nb_places': 1, 'mode_paiement': 'ORANGE_MONEY',
        })
        reservation = Reservation.objects.get(nom_passager='Dora')
        self.assertEqual(reservation.passager, passager)

    def test_deconnexion(self):
        passager = Passager(nom_complet='Eli', telephone='0995556666')
        passager.definir_mot_de_passe('motdepasse123')
        passager.save()
        self.client.post(reverse('compte_connexion'), {
            'telephone': '0995556666', 'mot_de_passe': 'motdepasse123',
        })
        self.client.get(reverse('compte_deconnexion'))
        self.assertIsNone(self.client.session.get('passager_id'))


class RappelDepartTests(TestCase):
    def setUp(self):
        self.route, self.bateau, self.traversee = creer_jeu_de_donnees()

    def test_commande_envoie_rappel_pour_depart_proche(self):
        from django.core.management import call_command
        from django.utils import timezone
        import io

        # traversée dans 2h, avec une réservation confirmée ayant un e-mail
        depart_proche = timezone.localtime() + timedelta(hours=2)
        self.traversee.date = depart_proche.date()
        self.traversee.heure = depart_proche.time()
        self.traversee.save()

        Reservation.objects.create(
            traversee=self.traversee, nom_passager="Faya", telephone="0996667777",
            email="faya@example.com", nb_places=1, total=10000,
            statut=Reservation.Statut.CONFIRME
        )
        out = io.StringIO()
        call_command('envoyer_rappels', stdout=out)
        reservation = Reservation.objects.get(nom_passager='Faya')
        self.assertTrue(reservation.rappel_envoye)

    def test_commande_ignore_depart_lointain(self):
        from django.core.management import call_command
        from django.utils import timezone
        import io

        depart_lointain = timezone.localtime() + timedelta(days=5)
        self.traversee.date = depart_lointain.date()
        self.traversee.heure = depart_lointain.time()
        self.traversee.save()

        Reservation.objects.create(
            traversee=self.traversee, nom_passager="Gaby", telephone="0997778888",
            email="gaby@example.com", nb_places=1, total=10000,
            statut=Reservation.Statut.CONFIRME
        )
        out = io.StringIO()
        call_command('envoyer_rappels', stdout=out)
        reservation = Reservation.objects.get(nom_passager='Gaby')
        self.assertFalse(reservation.rappel_envoye)


class ApiTests(TestCase):
    def setUp(self):
        self.route, self.bateau, self.traversee = creer_jeu_de_donnees()
        self.client = Client()

    def test_liste_traversees_api(self):
        r = self.client.get('/api/traversees/')
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(r.json()['count'], 1)

    def test_creation_reservation_api(self):
        r = self.client.post('/api/reservations/', {
            'traversee': self.traversee.id, 'nom_passager': 'Fred', 'telephone': '0991230000',
            'nb_places': 2, 'mode_paiement': 'CARTE',
        })
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()['statut'], 'EN_ATTENTE')

    def test_lecture_billet_par_code_api(self):
        reservation = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Gina", telephone="0", nb_places=1, total=10000
        )
        r = self.client.get(f'/api/reservations/{reservation.code}/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['code'], reservation.code)
