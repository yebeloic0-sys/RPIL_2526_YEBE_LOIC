# IFRI_MentorLink — Rattrapage Projet Intégrateur 2025–2026

Application web simplifiée permettant à un mentoré de rechercher un mentor
compatible **sans authentification**, à partir de :
- la compatibilité des matières / compétences,
- la compatibilité horaire (tolérance ± 1 heure).

## Stack technique

| Couche          | Technologie                                   |
|-----------------|------------------------------------------------|
| Frontend        | HTML / CSS / JavaScript (vanilla)              |
| Backend         | Python / Flask                                 |
| Base de données | **PostgreSQL** (via SQLAlchemy / Flask-SQLAlchemy) |

## Structure du projet

```
IFRI_MentorLink/
├── app.py              # Application Flask : routes web + API (validation, gestion d'erreurs)
├── config.py             # Configuration de connexion PostgreSQL
├── models.py               # Modèles SQLAlchemy : Mentor, Matiere, Disponibilite (+ contraintes CHECK)
├── matching.py               # Algorithme de matching (cœur du projet)
├── init_db.py                  # Crée les tables + insère les mentors de démo (via SQLAlchemy)
├── schema.sql                    # Alternative : crée les tables + données de démo en SQL pur (psql)
├── docker-compose.yml               # PostgreSQL prêt à l'emploi, sans installation locale
├── requirements.txt
├── requirements-dev.txt                # + pytest, pour lancer les tests
├── .env.example
├── tests/
│   └── test_matching.py                  # 26 tests unitaires de l'algorithme de matching
├── templates/
│   └── index.html                          # Page unique (formulaire + résultats)
└── static/
    ├── css/style.css
    └── js/script.js                          # Appel AJAX vers /api/match, affichage des résultats
```

## Installation (PostgreSQL)

### 1. Prérequis

- Python 3.10+
- PostgreSQL installé et démarré

### 2. Cloner et créer l'environnement virtuel

```bash
git clone <url-de-votre-depot>
cd IFRI_MentorLink
python3 -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Créer la base de données

**Option A — PostgreSQL déjà installé sur votre machine :**
```bash
createdb mentorlink
# ou, dans psql :
# CREATE DATABASE mentorlink;
```

**Option B — sans rien installer, via Docker :**
```bash
docker compose up -d
```
Cela démarre un PostgreSQL local sur le port 5432 avec les identifiants déjà
attendus par `.env.example` (base `mentorlink` créée automatiquement).

### 4. Configurer la connexion

```bash
cp .env.example .env
# Éditez .env et renseignez vos identifiants PostgreSQL si besoin
```

### 5. Créer les tables et les données de démonstration

**Option A — via le script Python (recommandé) :**
```bash
python init_db.py
```

**Option B — via SQL pur, directement avec psql :**
```bash
psql -d mentorlink -f schema.sql
```
N'utilisez qu'une seule des deux options (les deux créent les mêmes tables
et les mêmes 5 mentors de démonstration).

### 6. Lancer l'application

```bash
python app.py
```

Puis ouvrez **http://127.0.0.1:5000** dans votre navigateur.

## Robustesse de la base de données

Le schéma impose des règles d'intégrité directement au niveau de PostgreSQL,
pas seulement dans le code Python :
- `format_mentorat` ne peut être que `presentiel`, `en_ligne` ou `les_deux` (CHECK).
- `jour` ne peut être qu'un jour de la semaine valide (CHECK).
- `heure_debut` doit toujours être antérieure à `heure_fin` (CHECK).
- Suppression d'un mentor → ses matières et disponibilités sont supprimées
  automatiquement (`ON DELETE CASCADE`).
- Index sur `matiere.nom` et `disponibilite(mentor_id, jour)` pour des
  recherches rapides même avec beaucoup de mentors.
- `config.py` active `pool_pre_ping` : une connexion PostgreSQL qui a expiré
  après une période d'inactivité est automatiquement renouvelée au lieu de
  faire planter une requête.

## Tests automatisés

L'algorithme de matching est couvert par 26 tests unitaires (`tests/test_matching.py`) :
correspondance exacte, accents/casse, sigles (IA, ML, BD...), fautes de frappe,
correspondance partielle, absence de matière/jour/heure, créneau à la limite
exacte de la tolérance ±1h, mentors mal formés ou objets invalides, tri des
résultats, bonus de filière, etc. Ils s'exécutent sans base de données.

```bash
pip install -r requirements-dev.txt
pytest tests/ -v

# ou, sans installer pytest :
python tests/test_matching.py
```

## Comment fonctionne le matching

Un mentor apparaît dans les résultats seulement s'il remplit les **deux**
conditions imposées par le sujet :

1. **Au moins une matière en commun** avec la recherche du mentoré.
2. **Au moins un créneau de disponibilité compatible**, à ± 1 heure près.

L'algorithme (`matching.py`) est conçu pour être robuste face à une saisie
imparfaite, sans jamais planter :

- **Normalisation** : accents, majuscules/minuscules et espaces superflus
  sont ignorés (« Bases de Données » = « bases de donnees »).
- **Abréviations reconnues** : IA, ML, BD, SGBD, POO, IoT, GL, UX/UI, etc.
  retrouvent automatiquement leur forme complète.
- **Correspondance partielle** : rechercher « Python » retrouve un mentor
  dont l'intitulé est « Programmation Python avancée ».
- **Tolérance aux fautes de frappe** : une comparaison approximative
  (mot à mot) rattrape les petites erreurs de saisie (« Pyton » → « Python »).
- **Jour et/ou heure optionnels côté algorithme** : si l'un des deux manque,
  la recherche s'élargit au lieu d'échouer (le formulaire, lui, continue
  d'exiger les deux, conformément au sujet).
- **Tolérance aux données incomplètes** : un mentor sans disponibilité ou
  aux données mal formées est simplement écarté, jamais une cause de
  plantage — testé explicitement (mentors vides, `None`, listes malformées).
- **Résultats reproductibles** : tri par score décroissant puis par nom en
  cas d'égalité.

Un **score de compatibilité** (0 à 100) est ensuite calculé :

- 60 % du score = qualité et couverture des matières demandées retrouvées
  chez le mentor (1.0 si correspondance exacte, un peu moins si trouvée par
  alias, inclusion partielle ou ressemblance approximative).
- 40 % du score = qualité de la correspondance horaire (100 si l'heure tombe
  pile dans le créneau, dégressif jusqu'à 0 à la limite de la tolérance ±1h).
- +5 points bonus (non bloquant) si la filière renseignée correspond à celle
  du mentor.

Les résultats sont triés par score décroissant.

Le fichier `app.py` ajoute une couche de robustesse supplémentaire côté API :
validation stricte des champs (jour invalide, heure mal formée, JSON absent),
messages d'erreur clairs en français, gestion propre d'une panne de la base
de données (réponse 503 au lieu d'un plantage), et le matching lui-même est
entouré d'un filet de sécurité au cas où des données corrompues arriveraient
jusque-là.

## Soumission

- Renommez ce dépôt en `RPIL_2526_nom_prenom` avant de le pousser sur GitHub.
- Dépôt à soumettre avant le **samedi 4 juillet 2026, 15h**.
- Présentation en ligne prévue le **lundi 6 juillet 2026 à partir de 16h**.
