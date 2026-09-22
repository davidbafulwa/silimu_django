from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User, Group
from django.core import mail
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from .decorators import GROUPE_ADMIN, GROUPE_AGENT
from .models import (
    Port, Route, Bateau, Traversee, Reservation, Passager,
    Embarquement, Remboursement, HistoriqueReservation,
    RecompenseFidelite, NotificationInterne,
)
from . import services
from .notifications import payload_qr, verifier_signature


def creer_jeu_de_donnees():
    depart = Port.objects.create(nom="Munyaga", est_actif=True)
    arrivee = Port.objects.create(nom="Kasenyi", est_actif=True)
    route = Route.objects.create(port_depart=depart, port_arrivee=arrivee, distance_km=38, duree_min=75)
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


class ServiceAntiSurbookingTests(TestCase):
    """Le service de réservation atomic rejette la survente."""

    def setUp(self):
        self.route, self.bateau, self.traversee = creer_jeu_de_donnees()

    def test_reserver_place_au_dela_de_la_capacite_rejete(self):
        services.reserver_place(self.traversee, 5, nom_passager="A", telephone="1")
        with self.assertRaises(services.SurbookingError):
            services.reserver_place(self.traversee, 6, nom_passager="B", telephone="2")
        # la réservation rejetée n'a pas été créée
        self.assertEqual(Reservation.objects.filter(nom_passager="B").count(), 0)

    def test_reserver_place_calcule_total_et_statut_attente(self):
        r = services.reserver_place(self.traversee, 3, nom_passager="C", telephone="3")
        self.assertEqual(r.total, Decimal("30000"))
        self.assertEqual(r.statut, Reservation.Statut.EN_ATTENTE)
        self.assertIsNotNone(r.expire_le)


class ExpirationReservationsTests(TestCase):
    """La commande libère les places des paiements jamais effectués."""

    def setUp(self):
        self.route, self.bateau, self.traversee = creer_jeu_de_donnees()
        from django.utils import timezone

    def test_commande_expire_attentes_depassees(self):
        from django.core.management import call_command
        from django.utils import timezone
        import io

        ancienne = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Yann", telephone="1", nb_places=4,
            total=40000, statut=Reservation.Statut.EN_ATTENTE,
            expire_le=timezone.now() - timedelta(minutes=1),
        )
        future = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Zoe", telephone="2", nb_places=1,
            total=10000, statut=Reservation.Statut.EN_ATTENTE,
            expire_le=timezone.now() + timedelta(hours=1),
        )

        out = io.StringIO()
        call_command('expirer_reservations', stdout=out)

        ancienne.refresh_from_db()
        future.refresh_from_db()
        self.assertEqual(ancienne.statut, Reservation.Statut.ECHEC)
        self.assertIsNone(ancienne.expire_le)
        self.assertEqual(future.statut, Reservation.Statut.EN_ATTENTE)
        # 10 places de capacité : seule la réservation encore valide bloque 1 place
        self.assertEqual(self.traversee.places_disponibles(), 9)


class EmbarquementTests(TestCase):
    """Le contrôle d'embarquement au port valide chaque billet une seule fois."""

    def setUp(self):
        self.route, self.bateau, self.traversee = creer_jeu_de_donnees()
        Group.objects.get_or_create(name=GROUPE_AGENT)
        self.agent = User.objects.create_user('agent_emb', password='pass12345', is_staff=True)
        self.agent.groups.add(Group.objects.get(name=GROUPE_AGENT))
        self.client.force_login(self.agent)

    def test_scanner_valide_un_billet_confirme(self):
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Emile", telephone="0",
            nb_places=2, total=20000, statut=Reservation.Statut.CONFIRME
        )
        response = self.client.post(reverse('admin_embarquement'), {'code': r.code})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['resultat']['ok'])
        r.refresh_from_db()
        self.assertEqual(r.statut, Reservation.Statut.EMBARQUE)
        self.assertTrue(Embarquement.objects.filter(reservation=r, valide_par=self.agent).exists())

    def test_scanner_refuse_un_double_embarquement(self):
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Nora", telephone="1",
            nb_places=1, total=10000, statut=Reservation.Statut.CONFIRME
        )
        self.client.post(reverse('admin_embarquement'), {'code': r.code})
        self.client.post(reverse('admin_embarquement'), {'code': r.code})
        self.assertEqual(Embarquement.objects.filter(reservation=r).count(), 1)

    def test_scanner_refuse_un_billet_non_confirme(self):
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Polo", telephone="2",
            nb_places=1, total=10000, statut=Reservation.Statut.EN_ATTENTE
        )
        response = self.client.post(reverse('admin_embarquement'), {'code': r.code})
        self.assertFalse(response.context['resultat']['ok'])
        r.refresh_from_db()
        self.assertEqual(r.statut, Reservation.Statut.EN_ATTENTE)

    def test_manifeste_par_place_et_export_csv(self):
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Lina", telephone="3",
            nb_places=2, total=20000, statut=Reservation.Statut.CONFIRME
        )
        response = self.client.get(reverse('admin_manifest', args=[self.traversee.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['manifeste']), 2)
        csv = self.client.get(reverse('admin_manifest', args=[self.traversee.id]), {'export': 'csv'})
        self.assertEqual(csv.status_code, 200)
        self.assertIn('text/csv', csv['Content-Type'])

    def test_payload_qr_signe_et_verifie(self):
        code = "SLM-ABCD-1234"
        payload = payload_qr(code)
        code_extra, ok = payload.split(':')
        self.assertEqual(code_extra, code)
        self.assertTrue(verifier_signature(code, ok))
        self.assertFalse(verifier_signature(code, "0000000000"))

    def test_scanner_accepte_qr_signe_et_embarque(self):
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Salomé", telephone="4",
            nb_places=1, total=10000, statut=Reservation.Statut.CONFIRME
        )
        response = self.client.post(reverse('admin_embarquement'), {'code': payload_qr(r.code)})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['resultat']['ok'])
        r.refresh_from_db()
        self.assertEqual(r.statut, Reservation.Statut.EMBARQUE)

    def test_scanner_rejette_qr_falsifie(self):
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Robin", telephone="5",
            nb_places=1, total=10000, statut=Reservation.Statut.CONFIRME
        )
        response = self.client.post(
            reverse('admin_embarquement'), {'code': f"{r.code}:faussesignature"}
        )
        self.assertFalse(response.context['resultat']['ok'])
        self.assertIn('falsifié', response.context['resultat']['message'])
        r.refresh_from_db()
        self.assertEqual(r.statut, Reservation.Statut.CONFIRME)

    def test_scanner_accepte_url_du_billet(self):
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Uri", telephone="6",
            nb_places=1, total=10000, statut=Reservation.Statut.CONFIRME
        )
        url = f"https://billets.silimu.cd/billet/{r.code}"
        response = self.client.post(reverse('admin_embarquement'), {'code': url})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['resultat']['ok'])

    def test_scanner_ajax_renvoie_fiche_detaille(self):
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Ivonne", telephone="7",
            email="ivo@exemple.cd", nb_places=1, total=10000,
            statut=Reservation.Statut.CONFIRME, mode_paiement="ORANGE_MONEY"
        )
        response = self.client.post(
            reverse('admin_embarquement'), {'code': r.code, 'ajax': '1'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, r.code)
        self.assertContains(response, r.email)
        self.assertContains(response, "Ivonne")

    def test_fiche_scan_affiche_dates_reservation_et_embarquement(self):
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Fanny", telephone="8",
            nb_places=1, total=10000, statut=Reservation.Statut.CONFIRME
        )
        response = self.client.post(reverse('admin_embarquement'), {'code': r.code, 'ajax': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Réservé le")
        self.assertContains(response, timezone.localtime(r.date_creation).strftime("%d/%m/%Y"))
        emb = Embarquement.objects.get(reservation=r)
        self.assertContains(response, timezone.localtime(emb.date_embarquement).strftime("%d/%m/%Y"))
        self.assertContains(response, "agent_emb")

    def test_fiche_scan_billet_deja_utilise_montre_heure_exacte(self):
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Fred", telephone="9",
            nb_places=1, total=10000, statut=Reservation.Statut.CONFIRME
        )
        self.client.post(reverse('admin_embarquement'), {'code': r.code, 'ajax': '1'})
        emb = Embarquement.objects.get(reservation=r)
        response = self.client.post(reverse('admin_embarquement'), {'code': r.code, 'ajax': '1'})
        self.assertContains(response, "déjà utilisé")
        self.assertContains(response, timezone.localtime(emb.date_embarquement).strftime("%d/%m/%Y"))
        self.assertContains(response, "agent_emb")

    def test_billet_public_montre_date_reservation(self):
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Gael", telephone="10",
            nb_places=1, total=10000, statut=Reservation.Statut.CONFIRME
        )
        response = self.client.get(reverse('billet', args=[r.code]))
        self.assertContains(response, "Réservé le")
        self.assertContains(response, timezone.localtime(r.date_creation).strftime("%d/%m/%Y"))

    def test_billet_public_embarque_montre_heure_embarquement(self):
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Hugo", telephone="11",
            nb_places=1, total=10000, statut=Reservation.Statut.CONFIRME
        )
        self.client.post(reverse('admin_embarquement'), {'code': r.code})
        emb = Embarquement.objects.get(reservation=r)
        response = self.client.get(reverse('billet', args=[r.code]))
        self.assertContains(response, "Billet déjà utilisé")
        self.assertContains(response, timezone.localtime(emb.date_embarquement).strftime("%d/%m/%Y"))
        self.assertContains(response, "agent_emb")


class ArchivageAdminTests(TestCase):
    """Depuis Django admin, on archive un billet dans l'historique et on le
    masque de la liste active — sans détruire la donnée : le passager muni
    d'un compte continue de retrouver son billet."""

    def setUp(self):
        self.route, self.bateau, self.traversee = creer_jeu_de_donnees()
        Group.objects.get_or_create(name=GROUPE_ADMIN)
        self.admin = User.objects.create_user('admin_archive', password='pass12345', is_staff=True, is_superuser=True)
        self.admin.groups.add(Group.objects.get(name=GROUPE_ADMIN))
        self.client.force_login(self.admin)

    def test_action_admin_archive_masque_mais_garde_la_reservation(self):
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Arch", telephone="99",
            nb_places=2, total=20000, statut=Reservation.Statut.CONFIRME
        )
        Embarquement.objects.create(reservation=r, traversee=self.traversee, valide_par=self.admin)
        response = self.client.post(
            reverse('admin:reservations_reservation_changelist'),
            {'action': 'archiver_et_supprimer', '_selected_action': [str(r.pk)],
             'index': '0', 'select_across': '0'},
        )
        self.assertEqual(response.status_code, 302)
        r.refresh_from_db()
        self.assertTrue(r.archivee)
        arch = HistoriqueReservation.objects.get(code=r.code)
        self.assertEqual(arch.nom_passager, "Arch")
        self.assertEqual(arch.total, 20000)
        self.assertEqual(arch.statut, Reservation.Statut.CONFIRME)
        self.assertEqual(arch.embarquement_le, r.embarquement.date_embarquement)
        self.assertEqual(arch.archive_par, self.admin)

    def test_reservation_archivee_masquee_de_la_liste_admin_mais_visible_passager(self):
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Cache", telephone="97",
            nb_places=1, total=10000, statut=Reservation.Statut.CONFIRME
        )
        HistoriqueReservation.creer_depuis(r, archive_par=self.admin)
        r.archivee = True
        r.save(update_fields=['archivee'])
        changelist = self.client.get(reverse('admin:reservations_reservation_changelist'))
        self.assertNotContains(changelist, r.nom_passager)
        billet = self.client.get(reverse('billet', args=[r.code]))
        self.assertEqual(billet.status_code, 200)
        self.assertContains(billet, r.nom_passager)

    def test_archivage_garde_total_rembourse(self):
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Remb", telephone="98",
            nb_places=1, total=10000, statut=Reservation.Statut.ANNULE
        )
        Remboursement.objects.create(reservation=r, montant=10000, motif='ANNULATION', cree_par=self.admin)
        HistoriqueReservation.creer_depuis(r, archive_par=self.admin)
        arch = HistoriqueReservation.objects.get(code=r.code)
        self.assertEqual(arch.rembourse_total, 10000)
        self.assertTrue(Reservation.objects.filter(pk=r.pk).exists())


class FideliteTests(TestCase):
    """Tous les 10 voyages embarqués, un billet gratuit est attribué
    automatiquement : e-mail au dernier e-mail connu + notification interne."""

    def setUp(self):
        self.route, self.bateau, self.traversee = creer_jeu_de_donnees()
        Group.objects.get_or_create(name=GROUPE_AGENT)
        self.agent = User.objects.create_user('agent_fid', password='pass12345', is_staff=True)
        self.agent.groups.add(Group.objects.get(name=GROUPE_AGENT))
        self.client.force_login(self.agent)

    def _voyage(self, telephone, email=''):
        return Reservation.objects.create(
            traversee=self.traversee, nom_passager="Fid", telephone=telephone,
            email=email, nb_places=1, total=10000,
            statut=Reservation.Statut.EMBARQUE,
        )

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_recompense_au_10eme_voyage_envoie_email_et_notification(self):
        for _ in range(9):
            self._voyage('699')
        self._voyage('699', email='fidel@exemple.cd')
        from .fidelite import attribuer_recompense
        recompense = attribuer_recompense('699')
        self.assertIsNotNone(recompense)
        self.assertTrue(recompense.code.startswith('FID-'))
        self.assertEqual(recompense.seuil, 10)
        self.assertIsNotNone(recompense.envoye_le)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(recompense.code, mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ['fidel@exemple.cd'])
        self.assertTrue(NotificationInterne.objects.filter(
            type='FIDELITE', telephone='699', recompense=recompense
        ).exists())

    def test_pas_de_recompense_en_dessous_de_10(self):
        for _ in range(9):
            self._voyage('700')
        from .fidelite import attribuer_recompense
        self.assertIsNone(attribuer_recompense('700'))

    def test_recompense_unique_par_palier(self):
        for _ in range(12):
            self._voyage('701')
        from .fidelite import attribuer_recompense
        r1 = attribuer_recompense('701')
        self.assertIsNotNone(r1)
        self.assertIsNone(attribuer_recompense('701'))
        self.assertEqual(RecompenseFidelite.objects.filter(telephone='701').count(), 1)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_scan_du_10eme_voyage_attribue_la_recompense_automatiquement(self):
        for _ in range(9):
            self._voyage('702', email='scan@exemple.cd')
        r = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Scan", telephone='702',
            email='scan@exemple.cd', nb_places=1, total=10000,
            statut=Reservation.Statut.CONFIRME,
        )
        response = self.client.post(reverse('admin_embarquement'), {'code': r.code})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['resultat']['ok'])
        reward = RecompenseFidelite.objects.filter(telephone='702').first()
        self.assertIsNotNone(reward)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(NotificationInterne.objects.filter(recompense=reward).exists())


class StatutTraverseeTests(TestCase):
    """Annuler une traversée rembourse les billets payés et libère les attentes."""

    def setUp(self):
        self.route, self.bateau, self.traversee = creer_jeu_de_donnees()
        Group.objects.get_or_create(name=GROUPE_ADMIN)
        self.admin = User.objects.create_user('admin_trip', password='pass12345', is_staff=True)
        self.admin.groups.add(Group.objects.get(name=GROUPE_ADMIN))
        self.client.force_login(self.admin)

    def test_annulation_traversee_declenche_remboursement_et_echec_attentes(self):
        payee = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Anne", telephone="0",
            nb_places=2, total=20000, statut=Reservation.Statut.CONFIRME
        )
        attente = Reservation.objects.create(
            traversee=self.traversee, nom_passager="Bruno", telephone="1",
            nb_places=3, total=30000, statut=Reservation.Statut.EN_ATTENTE
        )
        response = self.client.post(
            reverse('admin_trip_statut', args=[self.traversee.id]),
            {'statut': Traversee.Statut.ANNULEE}
        )
        self.assertEqual(response.status_code, 302)

        payee.refresh_from_db()
        attente.refresh_from_db()
        self.assertEqual(payee.statut, Reservation.Statut.ANNULE)
        self.assertEqual(attente.statut, Reservation.Statut.ECHEC)
        remb = Remboursement.objects.get(reservation=payee)
        self.assertEqual(remb.motif, Remboursement.Motif.TRAVERSEE_ANNULEE)
        self.assertEqual(remb.montant, payee.total)

    def test_traversee_annulee_exclue_de_la_recherche(self):
        self.traversee.statut = Traversee.Statut.ANNULEE
        self.traversee.save()
        response = self.client.get(reverse('home'), {'depart': 'Munyaga'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['resultats']), [])

    def test_traversee_delete_refusee_si_reservations(self):
        Reservation.objects.create(
            traversee=self.traversee, nom_passager="C", telephone="2",
            nb_places=1, total=10000, statut=Reservation.Statut.CONFIRME
        )
        response = self.client.post(reverse('admin_trip_delete', args=[self.traversee.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Traversee.objects.filter(pk=self.traversee.pk).exists())
