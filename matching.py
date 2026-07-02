"""
Algorithme de matching mentoré <-> mentor.

Conçu pour être robuste face à une saisie imparfaite :
  - accents, majuscules/minuscules, espaces superflus ignorés,
  - abréviations courantes reconnues (IA, ML, BD, POO, IoT, GL...),
  - correspondance partielle ("Python" retrouve "Programmation Python avancée"),
  - tolérance aux fautes de frappe (comparaison approximative),
  - jour et/ou heure absents ou invalides gérés sans plantage,
  - un mentor mal formé (données manquantes) est ignoré, jamais fatal.

Un mentor n'apparaît dans les résultats que s'il remplit LES DEUX conditions
imposées par le sujet :
  1. Au moins une matière en commun avec la recherche.
  2. Au moins un créneau de disponibilité compatible, à ± 1 heure près.

Un score de compatibilité (0-100) est ensuite calculé pour classer les
résultats.
"""

import re
import unicodedata
import difflib

TOLERANCE_MINUTES = 60  # tolérance horaire imposée par le sujet : ± 1 heure
SEUIL_SIMILARITE = 0.82  # seuil de tolérance aux fautes de frappe (0-1)

# Jours acceptés, dans leur graphie canonique (celle stockée en base)
JOURS_CANONIQUES = (
    "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche",
)

# Abréviations / sigles courants -> forme longue normalisée.
# Permet à "IA" de retrouver "Intelligence Artificielle", etc.
ALIASES = {
    "ia": "intelligence artificielle",
    "ml": "machine learning",
    "dl": "deep learning",
    "bd": "bases de donnees",
    "sgbd": "bases de donnees",
    "sql": "bases de donnees",
    "poo": "programmation orientee objet",
    "iot": "internet des objets",
    "gl": "genie logiciel",
    "algo": "algorithmique",
    "ui": "interface utilisateur",
    "ux": "experience utilisateur",
    "reseau": "reseaux informatiques",
    "reseaux": "reseaux informatiques",
    "ds": "data science",
}


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def _normaliser(texte):
    """Nettoie une chaîne pour la comparaison : minuscules, sans accents,
    sans ponctuation superflue, espaces compactés. Ne lève jamais d'exception,
    quel que soit le type reçu."""
    if texte is None:
        return ""
    try:
        texte = str(texte).strip().lower()
    except Exception:
        return ""
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = re.sub(r"[^a-z0-9& ]", " ", texte)
    texte = re.sub(r"\s+", " ", texte).strip()
    return texte


_JOURS_NORMALISES = {_normaliser(j): j for j in JOURS_CANONIQUES}


def jour_canonique(jour):
    """Convertit une saisie de jour (quelle que soit sa casse/ses accents)
    vers sa graphie canonique, ou None si elle ne correspond à aucun jour."""
    return _JOURS_NORMALISES.get(_normaliser(jour))


# ---------------------------------------------------------------------------
# Correspondance des matières
# ---------------------------------------------------------------------------

def _meilleur_ratio_approche(demandee_norm, matiere_norm):
    """Similarité approximative la plus favorable entre deux chaînes : compare
    la chaîne entière, mais aussi mot à mot (utile quand la matière du mentor
    est une expression longue, ex : "pyton" doit pouvoir retrouver "python"
    dans "Programmation Python avancée")."""
    meilleur = difflib.SequenceMatcher(None, demandee_norm, matiere_norm).ratio()

    tokens_demandee = [t for t in demandee_norm.split() if len(t) >= 3]
    tokens_matiere = [t for t in matiere_norm.split() if len(t) >= 3]
    for td in tokens_demandee or [demandee_norm]:
        for tm in tokens_matiere or [matiere_norm]:
            ratio = difflib.SequenceMatcher(None, td, tm).ratio()
            if ratio > meilleur:
                meilleur = ratio
    return meilleur


def _score_correspondance_matiere(demandee_norm, matiere_norm):
    """Score de similarité [0, 1] entre une matière demandée et une matière
    proposée par un mentor (déjà normalisées). 0 = aucune correspondance."""
    if not demandee_norm or not matiere_norm:
        return 0.0

    # 1. Correspondance exacte
    if demandee_norm == matiere_norm:
        return 1.0

    # 2. Correspondance via abréviation/alias connu (dans les deux sens)
    if ALIASES.get(demandee_norm, demandee_norm) == ALIASES.get(matiere_norm, matiere_norm):
        return 0.95

    # 3. Une chaîne contient l'autre (ex : "python" dans "programmation python")
    if len(demandee_norm) >= 3 and (demandee_norm in matiere_norm or matiere_norm in demandee_norm):
        return 0.85

    # 4. Similarité approximative : tolère fautes de frappe, pluriels, etc.
    #    (comparaison chaîne entière ET mot à mot, cf. _meilleur_ratio_approche)
    ratio = _meilleur_ratio_approche(demandee_norm, matiere_norm)
    if ratio >= SEUIL_SIMILARITE:
        return round(0.55 + 0.15 * ratio, 2)

    return 0.0


def _matieres_correspondantes(mentor, matieres_recherchees):
    """Pour chaque matière demandée, cherche la meilleure matière proposée
    par le mentor qui lui correspond.
    Retourne (liste_des_matieres_du_mentor_retenues, score_matieres 0-100)."""

    if not isinstance(matieres_recherchees, (list, tuple)):
        matieres_recherchees = [matieres_recherchees] if matieres_recherchees else []

    demandees_norm = [_normaliser(m) for m in matieres_recherchees]
    demandees_norm = [m for m in demandees_norm if m]
    if not demandees_norm:
        return [], 0.0

    matieres_mentor = [
        (m.nom, _normaliser(m.nom))
        for m in (mentor.matieres or [])
        if getattr(m, "nom", None) and _normaliser(m.nom)
    ]
    if not matieres_mentor:
        return [], 0.0

    trouvees, poids = [], []
    for demandee_norm in demandees_norm:
        meilleur_nom, meilleur_score = None, 0.0
        for nom_original, nom_norm in matieres_mentor:
            s = _score_correspondance_matiere(demandee_norm, nom_norm)
            if s > meilleur_score:
                meilleur_score, meilleur_nom = s, nom_original
        if meilleur_score > 0:
            trouvees.append(meilleur_nom)
            poids.append(meilleur_score)

    if not trouvees:
        return [], 0.0

    trouvees_uniques = list(dict.fromkeys(trouvees))  # dédoublonne, garde l'ordre
    score = (sum(poids) / len(demandees_norm)) * 100
    return trouvees_uniques, round(min(score, 100.0), 1)


# ---------------------------------------------------------------------------
# Correspondance horaire
# ---------------------------------------------------------------------------

def _minutes(t):
    return t.hour * 60 + t.minute


def _ecart_minutes(cible, debut, fin):
    """Distance (en minutes) entre l'heure demandée et le créneau [debut, fin].
    0 si l'heure demandée tombe DANS le créneau."""
    c, d, f = _minutes(cible), _minutes(debut), _minutes(fin)
    if d <= c <= f:
        return 0
    return d - c if c < d else c - f


def _meilleure_disponibilite(mentor, jour=None, heure=None, tolerance=TOLERANCE_MINUTES):
    """Cherche, parmi les disponibilités du mentor, la meilleure correspondance :
      - jour ET heure fournis  -> ce jour précis, ± tolérance
      - jour seul               -> n'importe quel créneau ce jour-là
      - heure seule              -> n'importe quel jour, ± tolérance
      - ni l'un ni l'autre        -> le mentor est retenu s'il a au moins un créneau
    Retourne (ecart_minutes, disponibilite) ou None si rien ne convient."""

    disponibilites = mentor.disponibilites or []
    if not disponibilites:
        return None

    jour_norm = _normaliser(jour) if jour else None
    meilleure = None

    for dispo in disponibilites:
        if not getattr(dispo, "heure_debut", None) or not getattr(dispo, "heure_fin", None):
            continue  # créneau mal formé : ignoré, ne fait pas planter la recherche
        if jour_norm and _normaliser(dispo.jour) != jour_norm:
            continue

        ecart = 0
        if heure is not None:
            ecart = _ecart_minutes(heure, dispo.heure_debut, dispo.heure_fin)
            if ecart > tolerance:
                continue

        if meilleure is None or ecart < meilleure[0]:
            meilleure = (ecart, dispo)

    return meilleure


def _score_horaire(ecart_minutes, heure_fournie, tolerance=TOLERANCE_MINUTES):
    if not heure_fournie or tolerance <= 0:
        return 100.0
    return max(0.0, 100 - (ecart_minutes / tolerance) * 100)


# ---------------------------------------------------------------------------
# Calcul global
# ---------------------------------------------------------------------------

def calculer_compatibilite(mentor, matieres_recherchees, jour=None, heure=None, filiere=None):
    """Calcule la compatibilité entre un mentor et une recherche.
    Retourne un dict de résultat, ou None si le mentor est exclu.
    Ne lève jamais d'exception : un mentor aux données incomplètes est
    simplement exclu plutôt que de faire planter la recherche."""

    if mentor is None:
        return None

    matieres_trouvees, score_matieres = _matieres_correspondantes(mentor, matieres_recherchees)
    if not matieres_trouvees:
        return None  # condition 1 non remplie -> exclu

    dispo_match = _meilleure_disponibilite(mentor, jour, heure)
    if dispo_match is None:
        return None  # condition 2 non remplie -> exclu

    ecart_minutes, disponibilite = dispo_match
    score_horaire = _score_horaire(ecart_minutes, heure_fournie=heure is not None)

    score = (score_matieres * 0.6) + (score_horaire * 0.4)

    filiere_norm = _normaliser(filiere) if filiere else None
    filiere_compatible = bool(filiere_norm) and _normaliser(getattr(mentor, "filiere", "")) == filiere_norm
    if filiere_compatible:
        score = min(100.0, score + 5)

    return {
        "mentor": mentor,
        "matieres_communes": matieres_trouvees,
        "score": round(score, 1),
        "score_matieres": round(score_matieres, 1),
        "score_horaire": round(score_horaire, 1),
        "filiere_compatible": filiere_compatible,
        "disponibilite_correspondante": disponibilite,
    }


def trouver_mentors_compatibles(mentors, matieres_recherchees, jour=None, heure=None, filiere=None):
    """Filtre et trie la liste des mentors par score de compatibilité décroissant.
    Robuste : une erreur sur un mentor particulier ne fait jamais échouer
    la recherche globale, il est simplement ignoré."""
    resultats = []
    for mentor in (mentors or []):
        try:
            resultat = calculer_compatibilite(mentor, matieres_recherchees, jour, heure, filiere)
        except Exception:
            continue
        if resultat:
            resultats.append(resultat)

    # tri par score décroissant, puis par nom pour un ordre stable en cas d'égalité
    resultats.sort(key=lambda r: (-r["score"], (r["mentor"].nom or "").lower()))
    return resultats
