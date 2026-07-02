from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Formats de mentorat acceptés
FORMATS = ("presentiel", "en_ligne", "les_deux")

# Jours acceptés pour les disponibilités
JOURS = (
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche",
)


class Mentor(db.Model):
    __tablename__ = "mentor"
    __table_args__ = (
        db.CheckConstraint(
            "format_mentorat IN ('presentiel', 'en_ligne', 'les_deux')",
            name="ck_mentor_format_mentorat",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(120), nullable=False)
    filiere = db.Column(db.String(80), nullable=False)
    format_mentorat = db.Column(db.String(20), nullable=False, default="les_deux")

    matieres = db.relationship(
        "Matiere", backref="mentor", cascade="all, delete-orphan", lazy=True
    )
    disponibilites = db.relationship(
        "Disponibilite", backref="mentor", cascade="all, delete-orphan", lazy=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nom": self.nom,
            "filiere": self.filiere,
            "format_mentorat": self.format_mentorat,
            "matieres": [m.nom for m in self.matieres],
            "disponibilites": [d.to_dict() for d in self.disponibilites],
        }

    def __repr__(self):
        return f"<Mentor {self.id} {self.nom!r}>"


class Matiere(db.Model):
    __tablename__ = "matiere"
    __table_args__ = (
        db.Index("ix_matiere_nom", "nom"),
    )

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(80), nullable=False)
    mentor_id = db.Column(
        db.Integer, db.ForeignKey("mentor.id", ondelete="CASCADE"), nullable=False
    )

    def __repr__(self):
        return f"<Matiere {self.nom!r}>"


class Disponibilite(db.Model):
    __tablename__ = "disponibilite"
    __table_args__ = (
        db.CheckConstraint(
            "jour IN ('Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche')",
            name="ck_disponibilite_jour",
        ),
        db.CheckConstraint(
            "heure_debut < heure_fin", name="ck_disponibilite_heures_coherentes"
        ),
        db.Index("ix_disponibilite_mentor_jour", "mentor_id", "jour"),
    )

    id = db.Column(db.Integer, primary_key=True)
    jour = db.Column(db.String(20), nullable=False)
    heure_debut = db.Column(db.Time, nullable=False)
    heure_fin = db.Column(db.Time, nullable=False)
    mentor_id = db.Column(
        db.Integer, db.ForeignKey("mentor.id", ondelete="CASCADE"), nullable=False
    )

    def to_dict(self):
        return {
            "jour": self.jour,
            "heure_debut": self.heure_debut.strftime("%H:%M"),
            "heure_fin": self.heure_fin.strftime("%H:%M"),
        }

    def __repr__(self):
        return f"<Disponibilite {self.jour} {self.heure_debut}-{self.heure_fin}>"
