"""
Tests automatisés de l'algorithme de matching (matching.py).

Exécution :
    pip install pytest
    pytest tests/ -v

Ces tests utilisent de faux objets "mentor" (SimpleNamespace) pour tester
matching.py de façon totalement isolée, sans base de données ni Flask.
"""

import sys
from pathlib import Path
from datetime import time
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matching as mt


# ---------------------------------------------------------------------------
# Aides de construction
# ---------------------------------------------------------------------------

def matiere(nom):
    return NS(nom=nom)


def dispo(jour, h_debut, m_debut, h_fin, m_fin):
    return NS(jour=jour, heure_debut=time(h_debut, m_debut), heure_fin=time(h_fin, m_fin))


def mentor(nom="Mentor Test", filiere="IA", format_mentorat="les_deux",
           matieres=None, disponibilites=None):
    return NS(
        nom=nom,
        filiere=filiere,
        format_mentorat=format_mentorat,
        matieres=matieres if matieres is not None else [],
        disponibilites=disponibilites if disponibilites is not None else [],
    )


ELVIRE = mentor(
    nom="Elvire Kouassi",
    filiere="IA",
    matieres=[matiere("Programmation Python avancée"), matiere("Intelligence Artificielle")],
    disponibilites=[dispo("Lundi", 14, 0, 16, 0)],
)


# ---------------------------------------------------------------------------
# Correspondance des matières
# ---------------------------------------------------------------------------

def test_correspondance_exacte():
    r = mt.calculer_compatibilite(
        mentor(matieres=[matiere("Python")], disponibilites=[dispo("Lundi", 14, 0, 16, 0)]),
        ["Python"], "Lundi", time(15, 0),
    )
    assert r is not None
    assert r["score_matieres"] == 100.0


def test_insensible_a_la_casse_et_aux_accents():
    m = mentor(matieres=[matiere("Bases de Données")], disponibilites=[dispo("Lundi", 14, 0, 16, 0)])
    r = mt.calculer_compatibilite(m, ["  bases DE donnees  "], "lundi", time(15, 0))
    assert r is not None


def test_alias_sigle_reconnu():
    m = mentor(matieres=[matiere("Intelligence Artificielle")], disponibilites=[dispo("Lundi", 14, 0, 16, 0)])
    r = mt.calculer_compatibilite(m, ["IA"], "Lundi", time(15, 0))
    assert r is not None


def test_correspondance_partielle_sous_chaine():
    r = mt.calculer_compatibilite(ELVIRE, ["Python"], "Lundi", time(15, 0))
    assert r is not None
    assert "Programmation Python avancée" in r["matieres_communes"]


def test_tolerance_fautes_de_frappe():
    r = mt.calculer_compatibilite(ELVIRE, ["Pyhton"], "Lundi", time(15, 0))
    assert r is not None


def test_chaine_courte_pas_de_faux_positif_par_sous_chaine():
    # "ia" ne doit pas matcher par sous-chaîne dans un mot qui contient juste ces
    # deux lettres (ex. "diagramme") — seule une correspondance exacte ou par
    # alias/similarité doit être acceptée pour des chaînes aussi courtes.
    m = mentor(matieres=[matiere("Diagrammes UML")], disponibilites=[dispo("Lundi", 14, 0, 16, 0)])
    r = mt.calculer_compatibilite(m, ["ia"], "Lundi", time(15, 0))
    assert r is None


def test_aucune_matiere_commune_exclut_le_mentor():
    m = mentor(matieres=[matiere("Java")], disponibilites=[dispo("Lundi", 14, 0, 16, 0)])
    r = mt.calculer_compatibilite(m, ["Chimie"], "Lundi", time(15, 0))
    assert r is None


def test_matieres_demandees_dupliquees():
    m = mentor(matieres=[matiere("Python")], disponibilites=[dispo("Lundi", 14, 0, 16, 0)])
    r = mt.calculer_compatibilite(m, ["Python", "python", "  Python  "], "Lundi", time(15, 0))
    assert r is not None
    assert r["matieres_communes"] == ["Python"]  # dédoublonné


def test_plusieurs_matieres_score_partiel():
    m = mentor(matieres=[matiere("Python"), matiere("Java")], disponibilites=[dispo("Lundi", 14, 0, 16, 0)])
    r = mt.calculer_compatibilite(m, ["Python", "Chimie"], "Lundi", time(15, 0))
    assert r is not None
    assert 0 < r["score_matieres"] < 100  # une seule des deux matières demandées trouvée


# ---------------------------------------------------------------------------
# Correspondance horaire (tolérance ± 1h)
# ---------------------------------------------------------------------------

def test_heure_dans_le_creneau_score_horaire_maximal():
    r = mt.calculer_compatibilite(ELVIRE, ["Python"], "Lundi", time(15, 0))
    assert r["score_horaire"] == 100.0


def test_heure_a_exactement_60_minutes_est_acceptee():
    # créneau 14h-16h, demande à 17h -> écart de 60 min = limite incluse
    r = mt.calculer_compatibilite(ELVIRE, ["Python"], "Lundi", time(17, 0))
    assert r is not None
    assert r["score_horaire"] == 0.0  # à la limite exacte de la tolérance


def test_heure_a_61_minutes_est_refusee():
    r = mt.calculer_compatibilite(ELVIRE, ["Python"], "Lundi", time(17, 1))
    assert r is None


def test_jour_different_exclut_le_mentor():
    r = mt.calculer_compatibilite(ELVIRE, ["Python"], "Mardi", time(15, 0))
    assert r is None


def test_jour_non_fourni_recherche_sur_tous_les_jours():
    r = mt.calculer_compatibilite(ELVIRE, ["Python"], None, time(15, 0))
    assert r is not None


def test_mentor_sans_disponibilite_est_exclu():
    m = mentor(matieres=[matiere("Python")], disponibilites=[])
    r = mt.calculer_compatibilite(m, ["Python"], "Lundi", time(15, 0))
    assert r is None


def test_creneau_mal_forme_est_ignore_sans_planter():
    m = mentor(
        matieres=[matiere("Python")],
        disponibilites=[NS(jour="Lundi", heure_debut=None, heure_fin=None)],
    )
    r = mt.calculer_compatibilite(m, ["Python"], "Lundi", time(15, 0))
    assert r is None  # aucun créneau exploitable, mais pas de plantage


# ---------------------------------------------------------------------------
# Filière (bonus non bloquant) et score global
# ---------------------------------------------------------------------------

def test_bonus_filiere_ne_depasse_jamais_100():
    m = mentor(filiere="IA", matieres=[matiere("Python")], disponibilites=[dispo("Lundi", 14, 0, 16, 0)])
    r = mt.calculer_compatibilite(m, ["Python"], "Lundi", time(15, 0), filiere="IA")
    assert r["filiere_compatible"] is True
    assert r["score"] <= 100.0


def test_filiere_non_fournie_naffecte_pas_le_score():
    r1 = mt.calculer_compatibilite(ELVIRE, ["Python"], "Lundi", time(15, 0), filiere=None)
    r2 = mt.calculer_compatibilite(ELVIRE, ["Python"], "Lundi", time(15, 0), filiere="")
    assert r1["filiere_compatible"] is False
    assert r2["filiere_compatible"] is False


# ---------------------------------------------------------------------------
# Comportement de trouver_mentors_compatibles (robustesse globale)
# ---------------------------------------------------------------------------

def test_tri_par_score_decroissant():
    # Fort : les deux matières demandées + heure pile dans le créneau -> score 100
    fort = mentor(nom="Fort", matieres=[matiere("Python"), matiere("IA")],
                   disponibilites=[dispo("Lundi", 15, 0, 16, 0)])
    # Faible : une seule des deux matières + créneau décalé de 45 min (dans la
    # tolérance de 60 min, mais pénalisé) -> score plus bas, sans être exclu
    faible = mentor(nom="Faible", matieres=[matiere("Python")],
                     disponibilites=[dispo("Lundi", 15, 45, 16, 45)])
    res = mt.trouver_mentors_compatibles([faible, fort], ["Python", "IA"], "Lundi", time(15, 0))
    assert [r["mentor"].nom for r in res] == ["Fort", "Faible"]
    assert res[0]["score"] > res[1]["score"]


def test_liste_de_mentors_vide():
    res = mt.trouver_mentors_compatibles([], ["Python"], "Lundi", time(15, 0))
    assert res == []


def test_liste_mentors_none():
    res = mt.trouver_mentors_compatibles(None, ["Python"], "Lundi", time(15, 0))
    assert res == []


def test_objets_invalides_dans_la_liste_ne_plantent_pas():
    res = mt.trouver_mentors_compatibles(
        [ELVIRE, "pas un mentor", None, 42], ["Python"], "Lundi", time(15, 0)
    )
    assert len(res) == 1
    assert res[0]["mentor"] is ELVIRE


def test_aucune_matiere_demandee():
    res = mt.trouver_mentors_compatibles([ELVIRE], [], "Lundi", time(15, 0))
    assert res == []


def test_matieres_recherchees_en_chaine_plutot_que_liste():
    # défense supplémentaire si un appelant passe une chaîne au lieu d'une liste
    r = mt.calculer_compatibilite(ELVIRE, "Python", "Lundi", time(15, 0))
    assert r is not None


# ---------------------------------------------------------------------------
# jour_canonique
# ---------------------------------------------------------------------------

def test_jour_canonique_normalise_la_saisie():
    assert mt.jour_canonique("  LUNDI  ") == "Lundi"
    assert mt.jour_canonique("mércredi") == "Mercredi"


def test_jour_canonique_valeur_invalide():
    assert mt.jour_canonique("blah") is None
    assert mt.jour_canonique("") is None
    assert mt.jour_canonique(None) is None


if __name__ == "__main__":
    # Permet de lancer ce fichier avec "python tests/test_matching.py"
    # même si pytest n'est pas installé : exécute chaque test_* et rapporte
    # un résumé clair.
    import traceback

    tests = [(nom, fonc) for nom, fonc in list(globals().items())
              if nom.startswith("test_") and callable(fonc)]
    reussis, echecs = 0, []
    for nom, fonc in tests:
        try:
            fonc()
            reussis += 1
        except Exception:
            echecs.append((nom, traceback.format_exc()))

    print(f"\n{reussis}/{len(tests)} tests réussis.")
    for nom, trace in echecs:
        print(f"\nECHEC : {nom}\n{trace}")
    if echecs:
        sys.exit(1)
