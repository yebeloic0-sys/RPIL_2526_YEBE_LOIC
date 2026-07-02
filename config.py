import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration de l'application Flask — base de données PostgreSQL.

    L'URI de connexion se lit dans la variable d'environnement DATABASE_URL :
        postgresql+psycopg2://utilisateur:mot_de_passe@hote:5432/mentorlink

    Voir le fichier .env.example pour un modèle prêt à copier.
    """

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/mentorlink",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Options de connexion robustes : évite les erreurs "connexion perdue"
    # après une période d'inactivité (fréquent avec PostgreSQL en local).
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,   # vérifie la connexion avant chaque requête
        "pool_recycle": 280,     # recycle les connexions avant qu'elles expirent
    }

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-a-changer")
