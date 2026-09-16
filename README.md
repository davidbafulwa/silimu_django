# SILIMU — Gestion de réservation de billets de transport lacustre

Conception et réalisation d'une application web de gestion de réservation
de billets de transport lacustre : cas de l'établissement SILIMU.

Stack : **Django (Python) + PostgreSQL / Supabase**

<p align="center">
  <a href="https://www.python.org"><img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://www.djangoproject.com"><img src="https://img.shields.io/badge/Django-5.2-092E20?style=flat-square&logo=django&logoColor=white" alt="Django 5.2"></a>
  <a href="https://www.django-rest-framework.org"><img src="https://img.shields.io/badge/DRF-3.15-7f1d1d?style=flat-square&logo=django&logoColor=white" alt="Django REST Framework"></a>
  <a href="https://tailwindcss.com"><img src="https://img.shields.io/badge/Tailwind%20CSS-3-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white" alt="Tailwind CSS 3"></a>
  <a href="https://www.postgresql.org"><img src="https://img.shields.io/badge/PostgreSQL-14%2B-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL 14+"></a>
  <a href="https://supabase.com"><img src="https://img.shields.io/badge/Supabase-Auth%20%7C%20Storage-3ECF8E?style=flat-square&logo=supabase&logoColor=white" alt="Supabase"></a>
  <a href="https://www.cinetpay.com"><img src="https://img.shields.io/badge/Paiement-CinetPay%20Mobile%20Money-f47533?style=flat-square" alt="CinetPay Mobile Money"></a>
</p>
<p align="center">
  <a href="https://github.com/davidbafulwa/silimu_django"><img src="https://img.shields.io/badge/tests-28%20OK-success?style=flat-square" alt="Tests : 28 OK"></a>
  <a href="https://github.com/davidbafulwa/silimu_django"><img src="https://img.shields.io/github/last-commit/davidbafulwa/silimu_django?style=flat-square&label=dernier%20commit" alt="Dernier commit"></a>
  <a href="https://github.com/davidbafulwa/silimu_django"><img src="https://img.shields.io/github/contributors/davidbafulwa/silimu_django?style=flat-square&label=contributeurs" alt="Contributeurs"></a>
  <a href="https://github.com/davidbafulwa/silimu_django"><img src="https://img.shields.io/github/languages/count/davidbafulwa/silimu_django?style=flat-square&label=langages" alt="Langages"></a>
  <a href="https://github.com/davidbafulwa/silimu_django"><img src="https://img.shields.io/github/license/davidbafulwa/silimu_django?style=flat-square&label=licence" alt="Licence"></a>
</p>

## 1. Fonctionnalités

**Espace passager (public)**
- Recherche de traversées par port de départ, port d'arrivée et date (bateaux en maintenance automatiquement exclus)
- Tableau des départs avec places disponibles en temps réel (vue tableau sur ordinateur, vue cartes empilées sur mobile)
- Réservation d'un billet (nom, téléphone, e-mail facultatif, nombre de places, mode de paiement) — le nom du passager est auto-complété s'il a déjà réservé avec ce téléphone (historique des passagers)
- **Paiement réel via CinetPay** : Orange Money, Airtel Money, M-Pesa, carte bancaire
- Billet de confirmation avec **QR code réel**, imprimable, dont le statut reflète le vrai résultat du paiement
- **Envoi automatique du billet par e-mail** (avec QR code intégré) dès que le paiement est confirmé
- Retrouver ses billets par code ou par téléphone, ou via un **compte passager**
- **Compte passager** (inscription/connexion) : historique de toutes ses réservations, informations pré-remplies à chaque nouvelle réservation, rattachement automatique des réservations faites avant la création du compte
- **Rappel automatique par e-mail** avant le départ (délai configurable, ex: 24h avant)

**Back-office — deux rôles distincts**
- **Agent guichet** : vente de billets au comptoir en espèces (confirmation immédiate, sans passer par CinetPay), consultation et annulation des réservations
- **Administrateur** : tout ce que fait l'agent, plus la gestion des lignes, des bateaux (avec bascule *en service / en maintenance*), la programmation des traversées, le tableau de bord statistique avancé, et les exports comptables
- Authentification via comptes `is_staff`, rôle déterminé par groupe Django (`Administrateurs` / `Agents guichet`)
- Tableau de bord : recette totale, places vendues, paiements en attente, **taux de remplissage moyen**, **recette par ligne et par bateau (graphiques)**, répartition par mode de paiement
- **Export des réservations en CSV, Excel (.xlsx) et PDF**
- Alerte automatique par e-mail à l'équipe SILIMU quand une traversée atteint un taux de remplissage élevé
- Le site d'administration technique de Django (`/django-admin/`) est aussi disponible

**API REST** (pour une future application mobile native)
- Lecture publique des lignes, bateaux, traversées (`/api/lignes/`, `/api/bateaux/`, `/api/traversees/`)
- Création et consultation de réservations (`/api/reservations/`)

## 2. Architecture du projet

```
silimu_django/
├── manage.py
├── requirements.txt
├── MCD_MLD.md                 ← modélisation des données (à joindre au rapport)
├── silimu/                    ← configuration du projet
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py / asgi.py
└── reservations/               ← application principale
    ├── models.py               ← Route, Bateau, Traversee, Reservation
    ├── forms.py
    ├── views.py
    ├── api_views.py / serializers.py / api_urls.py   ← API REST (DRF)
    ├── cinetpay.py             ← intégration paiement Mobile Money
    ├── notifications.py        ← QR code, e-mail du billet, alerte remplissage
    ├── urls.py
    ├── admin.py                ← enregistrement dans /django-admin/
    ├── decorators.py           ← rôles admin / agent guichet
    ├── context_processors.py   ← expose le rôle courant aux templates
    ├── tests.py                ← tests unitaires et d'intégration
    ├── management/commands/
    │   ├── seed_data.py        ← jeu de données de démonstration
    │   ├── setup_roles.py      ← crée les groupes Administrateurs / Agents guichet
    │   └── envoyer_rappels.py  ← rappels de départ par e-mail (à planifier)
    └── templates/reservations/ ← toutes les pages HTML (+ templates e-mail)
```

## 3. Installation

### 3.1 Prérequis
- Python 3.11+
- PostgreSQL 14+ installé et démarré

### 3.2 Créer la base de données PostgreSQL

```bash
sudo -u postgres psql
```
```sql
CREATE DATABASE silimu_db;
CREATE USER silimu_user WITH PASSWORD 'silimu_pass';
ALTER ROLE silimu_user SET client_encoding TO 'utf8';
GRANT ALL PRIVILEGES ON DATABASE silimu_db TO silimu_user;
\q
```

### 3.3 Environnement Python

```bash
cd silimu_django
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3.4 Variables d'environnement (optionnel)

Par défaut, `silimu/settings.py` utilise `silimu_db` / `silimu_user` / `silimu_pass` /
`localhost` / `5432`. Pour changer ces valeurs sans modifier le code :

```bash
export DB_NAME=silimu_db
export DB_USER=silimu_user
export DB_PASSWORD=silimu_pass
export DB_HOST=localhost
export DB_PORT=5432
```

### 3.5 Migrations et démarrage

```bash
python manage.py migrate
python manage.py createsuperuser     # compte du back-office (répondre "yes" à staff/superuser)
python manage.py seed_data           # données de démonstration (lignes, bateaux, traversées)
python manage.py runserver
```

Ouvrir <http://127.0.0.1:8000/>

- Espace passager : `/`
- Mes billets : `/mes-billets/`
- Back-office : `/admin-silimu/connexion/` (identifiants du superuser créé plus haut)
- Admin technique Django : `/django-admin/`

Pour recharger le jeu de données depuis zéro :
```bash
python manage.py seed_data --reset
```

## 4. Créer les rôles (agent guichet / administrateur)

```bash
python manage.py setup_roles
```

Puis, dans un shell Django (`python manage.py shell`), attribue un rôle à un compte existant :
```python
from django.contrib.auth.models import User, Group
u = User.objects.get(username='nom_utilisateur')
u.is_staff = True
u.save()
u.groups.add(Group.objects.get(name='Agents guichet'))   # ou 'Administrateurs'
```

- Un **agent guichet** accède uniquement au comptoir (vente en espèces) et à la liste des réservations.
- Un **administrateur** (ou un superuser créé via `createsuperuser`) a accès à tout : statistiques, lignes, bateaux, traversées, exports.

## 5. Lancer les tests

```bash
python manage.py test reservations
```
28 tests couvrent : génération des codes de billet, calcul des places disponibles,
recherche, flux de paiement (succès/échec), rôles et permissions, vente au comptoir,
exports, et l'API REST.

## 6. Configurer le paiement Mobile Money (CinetPay)

L'application intègre [CinetPay](https://www.cinetpay.com), un agrégateur qui
accepte Orange Money, Airtel Money, M-Pesa et les cartes bancaires via une
seule API — disponible en RDC et dans plusieurs pays d'Afrique francophone.

1. Crée un compte marchand sur <https://www.cinetpay.com>
2. Dans le tableau de bord, va dans **Intégrations** pour récupérer ton `APIKEY` et ton `SITE_ID`
3. Renseigne ces informations comme variables d'environnement avant de lancer le serveur :

```bash
$env:CINETPAY_API_KEY = "ta_cle_api"      # PowerShell
$env:CINETPAY_SITE_ID = "ton_site_id"
$env:CINETPAY_CURRENCY = "CDF"            # ou XOF / XAF / GNF selon le pays
```

4. **Important** : CinetPay doit pouvoir appeler ton site depuis Internet pour
   confirmer les paiements (URL de notification). En développement local,
   utilise [ngrok](https://ngrok.com) :
```bash
ngrok http 8000
```
   puis lance `python manage.py runserver` normalement — CinetPay enverra
   ses notifications sur l'URL publique générée par ngrok si tu configures
   `ALLOWED_HOSTS` en conséquence.

5. Sans ces variables configurées, l'application reste pleinement
   fonctionnelle pour la démonstration : la réservation est créée avec le
   statut « Paiement échoué » et un message explicite s'affiche, sans jamais
   bloquer le passager.

**Flux de paiement mis en place :**
- Le passager choisit un mode de paiement (Orange Money, Airtel Money, M-Pesa, carte) et est redirigé vers la page de paiement sécurisée CinetPay
- CinetPay notifie automatiquement `/paiement/notification/` (webhook) une fois le paiement traité
- Le statut réel est toujours revérifié auprès de CinetPay (jamais fait confiance au seul webhook), aussi bien sur la page de notification que sur la page de retour `/paiement/retour/<code>/`
- Tant que le paiement n'est pas confirmé, les places ne sont pas comptées comme définitivement prises (statut « En attente » ou « Échec » exclus du calcul des places réservées)

## 7. Rappels automatiques avant le départ

La commande `envoyer_rappels` envoie un e-mail de rappel à tous les passagers
dont le départ approche (24h avant par défaut, réglable via `RAPPEL_HEURES_AVANT`).
Elle doit être exécutée périodiquement — Django n'a pas de planificateur intégré.

**Tester manuellement :**
```bash
python manage.py envoyer_rappels
```

**Planifier sous Windows (Planificateur de tâches) :**
1. Ouvrir "Planificateur de tâches" → Créer une tâche de base
2. Déclencheur : toutes les heures
3. Action : démarrer un programme
   - Programme : chemin complet vers `venv\Scripts\python.exe`
   - Arguments : `manage.py envoyer_rappels`
   - Démarrer dans : le dossier `silimu_django`

**Planifier sous Linux/Mac (cron) :**
```bash
crontab -e
```
Ajouter :
```
0 * * * * cd /chemin/vers/silimu_django && venv/bin/python manage.py envoyer_rappels
```

## 8. Adaptation mobile

Toutes les pages utilisent des classes responsives (Tailwind) : formulaires
en une colonne sur petit écran, menu qui s'adapte, et surtout le tableau des
départs qui bascule automatiquement en liste de cartes empilées sur mobile
au lieu du tableau large utilisé sur ordinateur. Aucune application séparée
n'est nécessaire : le même site s'adapte à la taille de l'écran.

## 9. Notes de conception

- Les places disponibles ne sont **pas** stockées en dur : elles sont calculées
  dynamiquement (`capacité du bateau − somme des réservations actives`), ce qui
  évite les incohérences en cas d'annulation.
- Le code du billet (`SLM-XXXX-9999`) est généré automatiquement et garanti unique.
- Une réservation annulée est conservée (traçabilité) mais libère ses places.
- Voir `MCD_MLD.md` pour le détail du modèle conceptuel et logique de données,
  directement réutilisable dans le chapitre « Conception » de votre rapport de TP.

## 10. Historique des évolutions

**Déjà en place dans ce livrable :**
- Paiement Mobile Money / carte réel (CinetPay)
- Vrai QR code scannable sur chaque billet (dans l'appli et dans l'e-mail)
- Envoi du billet par e-mail (SMS volontairement laissé de côté)
- **Compte passager** avec historique des réservations et rattachement automatique des réservations invité
- **Rappel automatique par e-mail avant le départ** (commande planifiable)
- Historique des passagers (auto-complétion du nom par téléphone, pour les invités)
- Rôles agent guichet / administrateur, vente en espèces au comptoir
- Statistiques avancées : recette par ligne/bateau, taux de remplissage, graphiques
- Bateaux en maintenance exclus automatiquement des réservations
- Exports CSV / Excel / PDF des réservations
- API REST (Django REST Framework)
- Alerte e-mail automatique quand une traversée est presque complète
- Tests unitaires (`reservations/tests.py`)

**Pistes encore ouvertes pour aller plus loin :**
- Vraie application mobile native consommant l'API REST
- Notifications SMS (non incluses ici à la demande du porteur du projet)
- Gestion fine des permissions par ligne/port pour de grandes flottes
- Tableau de bord avec export PDF directement des graphiques
