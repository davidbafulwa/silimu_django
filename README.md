# SILIMU — Gestion de réservation de billets de transport lacustre

Conception et réalisation d'une application web de gestion de réservation
de billets de transport lacustre : cas de l'établissement SILIMU.

Stack : **Django (Python) + SQLite (local) / PostgreSQL — Supabase (cloud)**

> 🚢 Application de conception, développement et design internes.

<p align="center">
  <a href="https://www.python.org"><img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="https://www.djangoproject.com"><img src="https://img.shields.io/badge/Django-5.2-092E20?style=flat-square&logo=django&logoColor=white" alt="Django 5.2"></a>
  <a href="https://www.django-rest-framework.org"><img src="https://img.shields.io/badge/DRF-3.15-7f1d1d?style=flat-square&logo=django&logoColor=white" alt="Django REST Framework"></a>
  <a href="https://tailwindcss.com"><img src="https://img.shields.io/badge/Tailwind%20CSS-3-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white" alt="Tailwind CSS 3"></a>
  <a href="https://www.sqlite.org"><img src="https://img.shields.io/badge/SQLite-local-003B57?style=flat-square&logo=sqlite&logoColor=white" alt="SQLite"></a>
  <a href="https://www.postgresql.org"><img src="https://img.shields.io/badge/PostgreSQL-14%2B-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL 14+"></a>
  <a href="https://supabase.com"><img src="https://img.shields.io/badge/Supabase-Auth%20%7C%20Storage-3ECF8E?style=flat-square&logo=supabase&logoColor=white" alt="Supabase"></a>
  <a href="https://www.cinetpay.com"><img src="https://img.shields.io/badge/Paiement-CinetPay%20Mobile%20Money-f47533?style=flat-square" alt="CinetPay Mobile Money"></a>
</p>
<p align="center">
  <a href="https://github.com/davidbafulwa/silimu_django"><img src="https://img.shields.io/badge/tests-54%20OK-success?style=flat-square" alt="Tests : 54 OK"></a>
  <a href="https://github.com/davidbafulwa/silimu_django"><img src="https://img.shields.io/github/last-commit/davidbafulwa/silimu_django?style=flat-square&label=dernier%20commit" alt="Dernier commit"></a>
  <a href="https://github.com/davidbafulwa/silimu_django"><img src="https://img.shields.io/github/contributors/davidbafulwa/silimu_django?style=flat-square&label=contributeurs" alt="Contributeurs"></a>
  <a href="https://github.com/davidbafulwa/silimu_django"><img src="https://img.shields.io/github/languages/count/davidbafulwa/silimu_django?style=flat-square&label=langages" alt="Langages"></a>
  <a href="https://github.com/davidbafulwa/silimu_django"><img src="https://img.shields.io/github/license/davidbafulwa/silimu_django?style=flat-square&label=licence" alt="Licence"></a>
</p>

## 1. Aperçu

**Espace passager**

<p align="center">
  <img src="screenshots/home.png" alt="Page d'accueil SILIMU" width="70%">
  <br>
  <img src="screenshots/reservation_form.png" alt="Formulaire de réservation" width="70%">
</p>

**Billet électronique et retrouver ses billets**

<p align="center">
  <img src="screenshots/billet_qr.png" alt="Billet électronique avec QR code" width="70%">
  <img src="screenshots/mes_billets.png" alt="Recherche de ses billets" width="70%">
</p>

**Back-office (agent guichet & administrateur) — contrôle d'embarquement par scan QR**

<p align="center">
  <img src="screenshots/admin_dashboard.png" alt="Tableau de bord admin" width="70%">
  <img src="screenshots/admin_reservations.png" alt="Réservations back-office" width="70%">
  <img src="screenshots/admin_comptoir.png" alt="Vente au comptoir" width="70%">
  <img src="screenshots/admin_traversees.png" alt="Programmation des traversées" width="70%">
</p>

## 2. Fonctionnalités

**Espace passager (public)**
- Recherche de traversées par port de départ, port d'arrivée et date (bateaux en maintenance automatiquement exclus)
- Tableau des départs avec places disponibles en temps réel (vue tableau sur ordinateur, vue cartes empilées sur mobile)
- Réservation d'un billet (nom, téléphone, e-mail facultatif, nombre de places, mode de paiement) — le nom du passager est auto-complété s'il a déjà réservé avec ce téléphone (historique des passagers)
- **Paiement réel via CinetPay** : Orange Money, Airtel Money, M-Pesa, carte bancaire
- Billet de confirmation avec **QR code réel**, imprimable, dont le statut reflète le vrai résultat du paiement
- **Envoi automatique du billet par e-mail** (avec QR code intégré) dès que le paiement est confirmé
- Retrouver ses billets par code ou par téléphone, ou via un **compte passager**
- **Compte passager** (inscription/connexion) : historique de toutes ses réservations, informations pré-remplies à chaque nouvelle réservation, rattachement automatique des réservations faites avant la création du compte, **progression du programme de fidélité**
- **Rappel automatique par e-mail** avant le départ (délai configurable, ex : 24h avant)
- **Programme de fidélité** : à chaque voyage embarqué le compteur avance ; au dixième voyage (puis 20ᵉ, 30ᵉ…), un **billet gratuit** est attribué automatiquement — e-mail de récompense envoyé au dernier e-mail du passager, code promotionnel `FID-XXXXXX` à présenter au comptoir

**Back-office — deux rôles distincts**
- **Agent guichet** : vente de billets au comptoir en espèces (confirmation immédiate, sans passer par CinetPay), consultation et annulation des réservations
- **Administrateur** : tout ce que fait l'agent, plus la gestion des lignes, des bateaux (avec bascule *en service / en maintenance*), la programmation des traversées, le tableau de bord statistique avancé, les exports comptables et **les notifications automatiques**
- **Contrôle d'embarquement par scan QR** (page `/admin-silimu/embarquement/`) : lecture du code via la **caméra** (bibliothèque jsQR, auto-hébergée) ou saisie manuelle ; contrôle anti-fraude — un billet déjà utilisé montre **la date et l'heure exactes du premier embarquement** ainsi que l'agent qui l'a validé
- **Archivage doux des réservations** : l'action « Archiver » masque une réservation de la liste Django admin tout en la **conservant dans l'historique** — le passager garde toujours l'accès à ses billets (compte, recherche, page billet)
- Authentification via comptes `is_staff`, rôle déterminé par groupe Django (`Administrateurs` / `Agents guichet`)
- Tableau de bord : recette totale, places vendues, paiements en attente, **taux de remplissage moyen**, **recette par ligne et par bateau (graphiques)**, répartition par mode de paiement, **notifications automatiques** (récompenses de fidélité, alertes système)
- **Export des réservations en CSV, Excel (.xlsx) et PDF**
- Alerte automatique par e-mail à l'équipe SILIMU quand une traversée atteint un taux de remplissage élevé
- Le site d'administration technique de Django (`/django-admin/`) est aussi disponible

**API REST** (pour une future application mobile native)
- Lecture publique des lignes, bateaux, traversées (`/api/lignes/`, `/api/bateaux/`, `/api/traversees/`)
- Création et consultation de réservations (`/api/reservations/`)

## 3. Architecture du projet

```
silimu_django/
├── manage.py
├── requirements.txt
├── MCD_MLD.md                 ← modélisation des données (à joindre au rapport)
├── certs/                     ← certificat local auto-signé (serveur HTTPS)
├── silimu/                    ← configuration du projet
│   ├── settings.py            ← SQLite par défaut, PostgreSQL via DATABASE_URL
│   ├── urls.py
│   ├── wsgi.py / asgi.py
└── reservations/               ← application principale
    ├── models.py               ← Route, Bateau, Traversee, Reservation,
    │                             Embarquement, HistoriqueReservation,
    │                             RecompenseFidelite, NotificationInterne
    ├── fidelite.py             ← programme de fidélité (10 voyages → 1 billet offert)
    ├── forms.py
    ├── views.py                ← y compris scanner d'embarquement (caméra QR)
    ├── api_views.py / serializers.py / api_urls.py   ← API REST (DRF)
    ├── cinetpay.py             ← intégration paiement Mobile Money
    ├── notifications.py        ← QR code, e-mail du billet, alerte remplissage, e-mail de récompense
    ├── urls.py
    ├── admin.py                ← /django-admin/ (dont archivage doux des réservations)
    ├── decorators.py           ← rôles admin / agent guichet
    ├── context_processors.py   ← expose le rôle courant aux templates
    ├── tests.py                ← 54 tests unitaires et d'intégration
    ├── migrations/             ← 0001 → 0008 (embarquements, historique, fidélité, archivage)
    ├── static/js/jsQR.js       ← lecteur de QR code auto-hébergé (aucun CDN requis)
    ├── management/commands/
    │   ├── seed_data.py        ← jeu de données de démonstration
    │   ├── setup_roles.py      ← crée les groupes Administrateurs / Agents guichet
    │   ├── create_admin.py     ← création d'un compte admin (mots de passe)
    │   ├── expirer_reservations.py ← expire les paiements en attente (à planifier)
    │   └── envoyer_rappels.py  ← rappels de départ par e-mail (à planifier)
    └── templates/reservations/ ← toutes les pages HTML (+ templates e-mail)
```

## 4. Installation

### 4.1 Prérequis
- Python 3.11+
- Base de données : **SQLite** (aucune installation, activé par défaut) **ou** PostgreSQL 14+ (option cloud)

> Par défaut (`DATABASE_URL` non définie), l'application tourne sur un **SQLite local** :
> fonctionne en ligne de commande et hors ligne, sans aucune configuration.

### 4.2 (Optionnel) Base de données PostgreSQL / Supabase

Pour une utilisation en production, définir `DATABASE_URL`, par exemple :

```bash
# PostgreSQL local
export DATABASE_URL="postgresql://silimu_user:silimu_pass@localhost:5432/silimu_db"

# Supabase (envoie le mot de passe en variable d'environnement, jamais dans le code)
export DATABASE_URL="postgresql://postgres:PASSWORD@db.XXXX.supabase.co:5432/postgres"
```

Sans `DATABASE_URL`, le projet utilise automatiquement `db.sqlite3` — rien à installer.

### 4.3 Environnement Python

```bash
cd silimu_django
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4.4 E-mail (Brevo)

Créer un fichier `.env` (ignoré par git) et renseigner :
- `DJANGO_EMAIL_BACKEND=reservations.brevo_email_backend.BrevoEmailBackend`
- `BREVO_API_KEY=...` et `BREVO_SENDER_EMAIL=...`

Sans configuration e-mail, l'application reste pleinement fonctionnelle pour la démonstration
(les e-mails sont simplement journalisés).

### 4.5 Migrations et démarrage

```bash
python manage.py migrate
python manage.py createsuperuser     # compte du back-office (répondre "yes" à staff/superuser)
python manage.py seed_data           # données de démonstration (lignes, bateaux, traversées)
python manage.py setup_roles         # groupes Administrateurs / Agents guichet
python manage.py runserver           # serveur HTTP (http://127.0.0.1:8000)
```

Ouvrir <http://127.0.0.1:8000/>

- Espace passager : `/`
- Mes billets : `/mes-billets/`
- Back-office : `/admin-silimu/connexion/` (identifiants du superuser créé plus haut)
- Contrôle d'embarquement (caméra) : `/admin-silimu/embarquement/`
- Admin technique Django : `/django-admin/`

**Pour la caméra sur un téléphone (scan QR), le contexte doit être sécurisé (HTTPS) :**

```bash
python manage.py runserver_plus 0.0.0.0:8443 --cert-file certs/cert.pem --key-file certs/key.pem
```

Puis ouvrir `https://<IP_LAN>:8443/` sur le téléphone (même Wi-Fi). Alternative sans HTTPS :
activer dans Chrome l'option `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
pour `http://<IP_LAN>:8000`.

Pour recharger le jeu de données depuis zéro :
```bash
python manage.py seed_data --reset
```

## 5. Créer les rôles (agent guichet / administrateur)

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
- Un **administrateur** (ou un superuser créé via `createsuperuser`) a accès à tout : statistiques, lignes, bateaux, traversées, exports, notifications.

## 6. Lancer les tests

```bash
python manage.py test reservations
```
**54 tests** couvrent : génération des codes de billet, calcul des places disponibles,
recherche, flux de paiement (succès/échec), rôles et permissions, vente au comptoir,
exports, API REST, dates d'embarquement et de réservation, archivage doux (masqué de
l'admin mais toujours visible par le passager) et programme de fidélité (récompense
au 10ᵉ voyage + e-mail, unicité par palier, déclenchement automatique au scan).

> 💡 Les tests s'exécutent sur une base SQLite locale : ils fonctionnent donc sur
> n'importe quelle machine, même sans `DATABASE_URL` (Supabase/Render) configurée.

## 7. Contrôle d'embarquement et anti-fraude

La page `/admin-silimu/embarquement/` permet à l'agent d'embarquer un passager :
- lecture du QR code du billet directement avec la **caméra** de son téléphone/PC
  (bibliothèque jsQR **auto-hébergée** dans `static/js/jsQR.js` — aucun CDN requis)
  ou **saisie manuelle** du code `SLM-XXXX-9999`
- à la validation, le billet passe au statut **Embarqué** (horodaté, agent enregistré)
- **anti-fraude** : présenter un billet déjà utilisé affiche la date et l'heure exactes
  du premier embarquement et l'agent concerné ; un billet annulé ou échoué est signalé
  clairement (bandeau rouge)

## 8. Programme de fidélité

- Seuil : **10 voyages embarqués = 1 billet gratuit** (puis 20ᵉ, 30ᵉ…)
- Compter les voyages et attribuer les récompenses : `reservations/fidelite.py`
- Le déclenchement est **automatique** au moment du scan d'embarquement
- Chaque récompense génère un code unique `FID-XXXXXX`, envoie un **e-mail automatique**
  au dernier e-mail connu du passager et crée une **notification interne** visible
  dans le tableau de bord du back-office
- Promotion affichée sur la page d'accueil et progression visible dans le compte passager

## 9. Configurer le paiement Mobile Money (CinetPay)

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
   confirmer les paiements (URL de notification).
5. Sans ces variables configurées, l'application reste pleinement fonctionnelle :
   la réservation est créée avec le statut « Paiement échoué » et un message explicite
   s'affiche, sans jamais bloquer le passager.

**Flux de paiement mis en place :**
- Le passager choisit un mode de paiement (Orange Money, Airtel Money, M-Pesa, carte) et est redirigé vers la page de paiement sécurisée CinetPay
- CinetPay notifie automatiquement `/paiement/notification/` (webhook) une fois le paiement traité
- Le statut réel est toujours revérifié auprès de CinetPay (jamais fait confiance au seul webhook), aussi bien sur la page de notification que sur la page de retour `/paiement/retour/<code>/`
- Tant que le paiement n'est pas confirmé, les places ne sont pas comptées comme définitivement prises (statut « En attente » ou « Échec » exclus du calcul des places réservées)
- Une commande optionnelle `expirer_reservations` bascule automatiquement les paiements en attente de longue durée en « Échec » (à planifier)

## 10. Rappels automatiques avant le départ

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

## 11. Adaptation mobile

Toutes les pages utilisent des classes responsives (Tailwind) : formulaires
en une colonne sur petit écran, menu qui s'adapte, et surtout le tableau des
départs qui bascule automatiquement en liste de cartes empilées sur mobile
au lieu du tableau large utilisé sur ordinateur. Le contrôle d'embarquement
est conçu pour être utilisé sur un téléphone (caméra + boutons pleine largeur).
Aucune application séparée n'est nécessaire : le même site s'adapte à la taille de l'écran.

> ℹ️ Tailwind est chargé par scripts (CDN) ; pour un fonctionnement 100 % hors ligne
> de l'interface, il est possible de télécharger localement `tailwindcss` (essentiel
> uniquement pour la démo hors ligne ; le scan QR, lui, fonctionne sans internet).

## 12. Notes de conception

- Les places disponibles ne sont **pas** stockées en dur : elles sont calculées
  dynamiquement (`capacité du bateau − somme des réservations actives`), ce qui
  évite les incohérences en cas d'annulation.
- Le code du billet (`SLM-XXXX-9999`) est généré automatiquement et garanti unique.
- Un billet embarqué est horodaté et ne peut être embarqué deux fois (enregistrement
  de l'agent et de l'instant exact du premier passage).
- L'archivage doux (`Reservation.archivee`) masque la réservation des vues admin
  **sans la supprimer** ; une copie complète est aussi conservée dans
  `HistoriqueReservation` (traçabilité totale).
- Voir `MCD_MLD.md` pour le détail du modèle conceptuel et logique de données,
  directement réutilisable dans le chapitre « Conception » de votre rapport de TP.

## 13. Historique des évolutions

**Déjà en place dans ce livrable :**
- Paiement Mobile Money / carte réel (CinetPay)
- Vrai QR code scannable sur chaque billet (dans l'appli et dans l'e-mail)
- Envoi du billet par e-mail (SMS volontairement laissé de côté)
- **Compte passager** avec historique des réservations et rattachement automatique des réservations invité
- **Contrôle d'embarquement par scan QR caméra** (jsQR auto-hébergé) + anti-fraude
  (un billet déjà utilisé affiche la date/heure exacte du premier embarquement et l'agent)
- **Programme de fidélité** : 10 voyages embarqués → 1 billet gratuit, attribution automatique
  au scan, e-mail de récompense, notification back-office, progression dans le compte passager
- **Archivage doux** des réservations dans l'admin (masquées de la liste mais jamais perdues,
  le passager garde toujours l'accès à ses billets)
- **Rappel automatique par e-mail avant le départ** (commande planifiable)
- Historique des passagers (auto-complétion du nom par téléphone, pour les invités)
- Rôles agent guichet / administrateur, vente en espèces au comptoir
- Statistiques avancées : recette par ligne/bateau, taux de remplissage, graphiques, notifications
- Bateaux en maintenance exclus automatiquement des réservations
- Exports CSV / Excel / PDF des réservations
- API REST (Django REST Framework)
- Alerte e-mail automatique quand une traversée est presque complète
- Tests unitaires (`reservations/tests.py`) — 54 tests

**Pistes encore ouvertes pour aller plus loin :**
- Vraie application mobile native consommant l'API REST
- Notifications SMS (non incluses ici à la demande du porteur du projet)
- Utilisation du code fidélité `FID-…` directement au comptoir (billet à 0 FC)
- Gestion fine des permissions par ligne/port pour de grandes flottes
- Tableau de bord avec export PDF directement des graphiques