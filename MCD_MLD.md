# Modélisation des données — SILIMU

Application web de gestion de réservation de billets de transport lacustre
Cas de l'établissement SILIMU

## 1. Dictionnaire des données

| Entité | Attribut | Type | Contrainte |
|---|---|---|---|
| Passager | id | Entier | Clé primaire |
| | nom_complet | Texte | Non nul |
| | telephone | Texte | Non nul, unique |
| | email | Texte | Facultatif |
| | mot_de_passe | Texte | Haché (jamais stocké en clair) |
| | date_inscription | Date/heure | Auto |
| Route (Ligne) | id | Entier | Clé primaire |
| | port_depart | Texte | Non nul |
| | port_arrivee | Texte | Non nul |
| | distance_km | Entier | Non nul |
| | duree_min | Entier | Non nul |
| Bateau | id | Entier | Clé primaire |
| | nom | Texte | Non nul, unique |
| | capacite | Entier | Non nul |
| | type_bateau | Texte (choix) | Vedette rapide / Ferry / Pirogue motorisée |
| | en_service | Booléen | Défaut: vrai |
| Traversee | id | Entier | Clé primaire |
| | route_id | Entier | Clé étrangère → Route |
| | bateau_id | Entier | Clé étrangère → Bateau |
| | date | Date | Non nul |
| | heure | Heure | Non nul |
| | prix | Décimal | Non nul |
| Reservation | id | Entier | Clé primaire |
| | traversee_id | Entier | Clé étrangère → Traversee |
| | passager_id | Entier | Clé étrangère → Passager (facultatif, invité possible) |
| | code | Texte | Unique, généré automatiquement |
| | nom_passager | Texte | Non nul |
| | telephone | Texte | Non nul |
| | nb_places | Entier | Non nul, ≥ 1 |
| | total | Décimal | Non nul |
| | mode_paiement | Texte (choix) | Orange Money / Airtel Money / M-Pesa / Carte bancaire |
| | statut | Texte (choix) | En attente / Confirmé / Échec / Annulé |
| | date_creation | Date/heure | Auto |

## 2. Modèle Conceptuel de Données (MCD)

```
┌───────────────┐          ┌───────────────┐
│     ROUTE     │          │     BATEAU    │
│───────────────│          │───────────────│
│ id (id)       │          │ id (id)       │
│ port_depart   │          │ nom           │
│ port_arrivee  │          │ capacite      │
│ distance_km   │          │ type_bateau   │
│ duree_min     │          │ en_service    │
└───────┬───────┘          └───────┬───────┘
        │ 1                        │ 1
        │                          │
        │        dessert           │ opère
        │  (1,n)            (1,n)  │
        └───────────┬──────────────┘
                     │
              ┌──────▼───────┐
              │  TRAVERSEE   │
              │──────────────│
              │ id (id)      │
              │ date         │
              │ heure        │
              │ prix         │
              └──────┬───────┘
                      │ 1
                      │
                concerne
                (0,n)
                      │
              ┌───────▼────────┐
              │   RESERVATION  │
              │────────────────│
              │ id (id)        │
              │ code           │
              │ nom_passager   │
              │ telephone      │
              │ nb_places      │
              │ total          │
              │ statut         │
              │ date_creation  │
              └────────────────┘
```

**Règles de gestion :**
1. Une ligne (Route) relie toujours exactement deux ports (départ et arrivée) et peut être desservie par plusieurs traversées.
2. Un bateau peut assurer plusieurs traversées, mais une traversée est assurée par un seul bateau.
3. Une traversée correspond à une ligne + un bateau + une date + une heure + un prix.
4. Une réservation porte toujours sur une seule traversée ; une traversée peut recevoir plusieurs réservations, jusqu'à saturation de la capacité du bateau.
5. Le nombre de places disponibles sur une traversée = capacité du bateau − somme des places des réservations dont le paiement est confirmé ou en attente (les réservations annulées ou en échec de paiement ne comptent pas).
6. Une réservation est créée avec le statut « En attente » dès que le passager valide le formulaire, puis passe à « Confirmé » ou « Échec » selon le résultat réel du paiement Mobile Money (vérifié auprès de l'opérateur de paiement, jamais supposé).
7. Une réservation annulée ou en échec libère les places qu'elle occupait, sans être supprimée (traçabilité).
8. Le code du billet est unique et généré automatiquement à la création de la réservation ; il sert aussi d'identifiant de transaction auprès de l'opérateur de paiement.

## 3. Modèle Logique de Données (MLD) — relationnel

```
ROUTE (id, port_depart, port_arrivee, distance_km, duree_min)

BATEAU (id, nom, capacite, type_bateau, en_service)

TRAVERSEE (id, #route_id, #bateau_id, date, heure, prix)
   #route_id  → référence ROUTE(id)
   #bateau_id → référence BATEAU(id)
   Contrainte d'unicité : (route_id, bateau_id, date, heure)

RESERVATION (id, #traversee_id, code, nom_passager, telephone,
             nb_places, total, statut, date_creation)
   #traversee_id → référence TRAVERSEE(id)
   Contrainte d'unicité : (code)
```

**Cardinalités résumées :**
- ROUTE (1,n) —— (1,1) TRAVERSEE
- BATEAU (1,n) —— (1,1) TRAVERSEE
- TRAVERSEE (1,n) —— (0,n) RESERVATION *(en pratique 0,1 côté Traversee→Reservation n'existe pas: une traversée a 0..n réservations, une réservation a exactement 1 traversée)*

## 4. Correspondance avec les modèles Django

| Entité MCD/MLD | Modèle Django (`reservations/models.py`) |
|---|---|
| ROUTE | `Route` |
| BATEAU | `Bateau` |
| TRAVERSEE | `Traversee` |
| RESERVATION | `Reservation` |

Les clés étrangères sont implémentées avec `models.ForeignKey(..., on_delete=models.CASCADE)`,
et les contraintes d'unicité avec `models.UniqueConstraint` dans la classe `Meta` de chaque modèle.
