"""
Initialise la base de données : crée les tables puis insère des mentors
de démonstration (au moins 3, imposé par le sujet).

Utilisation :
    python init_db.py
"""

from datetime import time

from app import app
from models import db, Mentor, Matiere, Disponibilite


def creneau(jour, h_debut, m_debut, h_fin, m_fin):
    return Disponibilite(
        jour=jour,
        heure_debut=time(h_debut, m_debut),
        heure_fin=time(h_fin, m_fin),
    )


MENTORS_DEMO = [
    {
        "nom": "Elvire Kouassi",
        "filiere": "IA",
        "format_mentorat": "les_deux",
        "matieres": ["Intelligence Artificielle", "Python", "Machine Learning", "Mathématiques"],
        "disponibilites": [
            ("Lundi", 14, 0, 16, 0),
            ("Mercredi", 10, 0, 12, 0),
        ],
    },
    {
        "nom": "Rafiou Dossou",
        "filiere": "GL",
        "format_mentorat": "en_ligne",
        "matieres": ["Génie Logiciel", "Java", "UML", "Gestion de projet"],
        "disponibilites": [
            ("Mardi", 9, 0, 11, 0),
            ("Jeudi", 15, 0, 17, 0),
        ],
    },
    {
        "nom": "Chimène Agbossou",
        "filiere": "SI",
        "format_mentorat": "presentiel",
        "matieres": ["Bases de données", "SQL", "Modélisation", "Power BI"],
        "disponibilites": [
            ("Mercredi", 14, 0, 16, 0),
            ("Vendredi", 9, 0, 11, 0),
        ],
    },
    {
        "nom": "Marius Tossou",
        "filiere": "SE&IoT",
        "format_mentorat": "les_deux",
        "matieres": ["Réseaux", "IoT", "Systèmes embarqués", "C"],
        "disponibilites": [
            ("Lundi", 8, 0, 10, 0),
            ("Samedi", 10, 0, 12, 0),
        ],
    },
    {
        "nom": "Nadège Hounkpe",
        "filiere": "IM",
        "format_mentorat": "en_ligne",
        "matieres": ["Algorithmique", "Python", "Structures de données"],
        "disponibilites": [
            ("Jeudi", 10, 0, 12, 0),
            ("Vendredi", 15, 0, 17, 0),
        ],
    },
]


def main():
    with app.app_context():
        db.create_all()

        if Mentor.query.count() > 0:
            print("La base contient déjà des mentors. Aucune donnée ajoutée.")
            print(f"Mentors existants : {Mentor.query.count()}")
            return

        for data in MENTORS_DEMO:
            mentor = Mentor(
                nom=data["nom"],
                filiere=data["filiere"],
                format_mentorat=data["format_mentorat"],
            )
            mentor.matieres = [Matiere(nom=nom) for nom in data["matieres"]]
            mentor.disponibilites = [
                creneau(*slot) for slot in data["disponibilites"]
            ]
            db.session.add(mentor)

        db.session.commit()
        print(f"{len(MENTORS_DEMO)} mentors insérés avec succès.")


if __name__ == "__main__":
    main()
