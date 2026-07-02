-- Schéma PostgreSQL pour IFRI_MentorLink
-- Alternative à "python init_db.py" : à exécuter directement avec psql si vous
-- préférez créer les tables vous-même.
--
--   createdb mentorlink
--   psql -d mentorlink -f schema.sql
--
-- Les contraintes CHECK ci-dessous garantissent l'intégrité des données
-- directement au niveau de la base (indépendamment de l'application).

BEGIN;

DROP TABLE IF EXISTS disponibilite CASCADE;
DROP TABLE IF EXISTS matiere CASCADE;
DROP TABLE IF EXISTS mentor CASCADE;

CREATE TABLE mentor (
    id               SERIAL PRIMARY KEY,
    nom              VARCHAR(120) NOT NULL,
    filiere          VARCHAR(80)  NOT NULL,
    format_mentorat  VARCHAR(20)  NOT NULL DEFAULT 'les_deux'
                     CHECK (format_mentorat IN ('presentiel', 'en_ligne', 'les_deux'))
);

CREATE TABLE matiere (
    id         SERIAL PRIMARY KEY,
    nom        VARCHAR(80) NOT NULL,
    mentor_id  INTEGER NOT NULL REFERENCES mentor(id) ON DELETE CASCADE
);

CREATE INDEX ix_matiere_nom ON matiere (nom);

CREATE TABLE disponibilite (
    id           SERIAL PRIMARY KEY,
    jour         VARCHAR(20) NOT NULL
                 CHECK (jour IN ('Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche')),
    heure_debut  TIME NOT NULL,
    heure_fin    TIME NOT NULL,
    mentor_id    INTEGER NOT NULL REFERENCES mentor(id) ON DELETE CASCADE,
    CHECK (heure_debut < heure_fin)
);

CREATE INDEX ix_disponibilite_mentor_jour ON disponibilite (mentor_id, jour);

-- Données de démonstration (5 mentors, cohérent avec init_db.py)

INSERT INTO mentor (nom, filiere, format_mentorat) VALUES
    ('Elvire Kouassi', 'IA', 'les_deux'),
    ('Rafiou Dossou', 'GL', 'en_ligne'),
    ('Chimène Agbossou', 'SI', 'presentiel'),
    ('Marius Tossou', 'SE&IoT', 'les_deux'),
    ('Nadège Hounkpe', 'IM', 'en_ligne');

INSERT INTO matiere (nom, mentor_id) VALUES
    ('Intelligence Artificielle', 1), ('Python', 1), ('Machine Learning', 1), ('Mathématiques', 1),
    ('Génie Logiciel', 2), ('Java', 2), ('UML', 2), ('Gestion de projet', 2),
    ('Bases de données', 3), ('SQL', 3), ('Modélisation', 3), ('Power BI', 3),
    ('Réseaux', 4), ('IoT', 4), ('Systèmes embarqués', 4), ('C', 4),
    ('Algorithmique', 5), ('Python', 5), ('Structures de données', 5);

INSERT INTO disponibilite (jour, heure_debut, heure_fin, mentor_id) VALUES
    ('Lundi', '14:00', '16:00', 1), ('Mercredi', '10:00', '12:00', 1),
    ('Mardi', '09:00', '11:00', 2), ('Jeudi', '15:00', '17:00', 2),
    ('Mercredi', '14:00', '16:00', 3), ('Vendredi', '09:00', '11:00', 3),
    ('Lundi', '08:00', '10:00', 4), ('Samedi', '10:00', '12:00', 4),
    ('Jeudi', '10:00', '12:00', 5), ('Vendredi', '15:00', '17:00', 5);

COMMIT;
