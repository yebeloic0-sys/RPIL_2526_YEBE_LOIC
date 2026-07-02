import logging
from datetime import datetime

from flask import Flask, render_template, request, jsonify
from sqlalchemy.exc import SQLAlchemyError

from config import Config
from models import db, Mentor
from matching import trouver_mentors_compatibles, jour_canonique, JOURS_CANONIQUES

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ifri_mentorlink")

MAX_MATIERES = 15  # garde-fou contre un payload abusif


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/mentors", methods=["GET"])
def liste_mentors():
    """Optionnel : renvoie tous les mentors, utile pour vérifier le seed."""
    try:
        mentors = Mentor.query.all()
    except SQLAlchemyError:
        logger.exception("Erreur base de données sur /api/mentors")
        return jsonify({"erreurs": ["Base de données indisponible."]}), 503
    return jsonify([m.to_dict() for m in mentors])


def _valider_payload(payload):
    """Valide et nettoie les données reçues. Retourne (donnees_propres, erreurs)."""
    erreurs = []

    matieres = payload.get("matieres", [])
    if isinstance(matieres, str):
        matieres = matieres.split(",")
    if not isinstance(matieres, list):
        matieres = []
    matieres = [str(m).strip() for m in matieres if str(m).strip()]
    matieres = list(dict.fromkeys(matieres))[:MAX_MATIERES]  # dédoublonne + limite

    if not matieres:
        erreurs.append("Veuillez indiquer au moins une matière ou compétence recherchée.")

    jour_brut = (payload.get("jour") or "").strip()
    jour = jour_canonique(jour_brut) if jour_brut else None
    if not jour_brut:
        erreurs.append("Veuillez indiquer un jour de disponibilité.")
    elif jour is None:
        erreurs.append(
            "Jour invalide. Choisissez parmi : " + ", ".join(JOURS_CANONIQUES) + "."
        )

    heure_str = (payload.get("heure") or "").strip()
    heure = None
    if not heure_str:
        erreurs.append("Veuillez indiquer une heure souhaitée.")
    else:
        try:
            heure = datetime.strptime(heure_str, "%H:%M").time()
        except (ValueError, TypeError):
            erreurs.append("Format d'heure invalide (attendu HH:MM).")

    filiere = (payload.get("filiere") or "").strip() or None

    return {"matieres": matieres, "jour": jour, "heure": heure, "filiere": filiere}, erreurs


@app.route("/api/match", methods=["POST"])
def api_match():
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"erreurs": ["Requête invalide : JSON attendu."]}), 400

    donnees, erreurs = _valider_payload(payload)
    if erreurs:
        return jsonify({"erreurs": erreurs}), 400

    try:
        mentors = Mentor.query.all()
    except SQLAlchemyError:
        logger.exception("Erreur base de données sur /api/match")
        return jsonify({"erreurs": ["Base de données indisponible. Réessayez plus tard."]}), 503

    try:
        resultats = trouver_mentors_compatibles(
            mentors,
            donnees["matieres"],
            donnees["jour"],
            donnees["heure"],
            donnees["filiere"],
        )
    except Exception:
        # L'algorithme de matching est conçu pour ne jamais lever d'exception,
        # mais on se protège quand même de tout imprévu (ex : données corrompues).
        logger.exception("Erreur inattendue pendant le matching")
        return jsonify({"erreurs": ["Une erreur inattendue est survenue pendant la recherche."]}), 500

    reponse = []
    for r in resultats:
        mentor = r["mentor"]
        dispo = r["disponibilite_correspondante"]
        reponse.append({
            "nom": mentor.nom,
            "filiere": mentor.filiere,
            "format_mentorat": mentor.format_mentorat,
            "matieres_communes": r["matieres_communes"],
            "disponibilites": [d.to_dict() for d in mentor.disponibilites],
            "creneau_correspondant": dispo.to_dict(),
            "score": r["score"],
            "score_matieres": r["score_matieres"],
            "score_horaire": r["score_horaire"],
            "filiere_compatible": r["filiere_compatible"],
        })

    return jsonify({"resultats": reponse, "nombre": len(reponse)})


@app.errorhandler(404)
def non_trouve(_e):
    return jsonify({"erreurs": ["Ressource introuvable."]}), 404


@app.errorhandler(500)
def erreur_serveur(_e):
    return jsonify({"erreurs": ["Erreur interne du serveur."]}), 500


if __name__ == "__main__":
    app.run(debug=True)
