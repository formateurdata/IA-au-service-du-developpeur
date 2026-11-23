"""Réglages partagés : la clé et le modèle de conversation."""
import os
from pathlib import Path

RACINE_API = Path(__file__).resolve().parent.parent
FICHIER_ENV = RACINE_API / ".env"

MODELE = "gpt-4o-mini"


def cle() -> str:
    """La clé, lue dans l'environnement, sinon dans api/.env."""
    valeur = os.environ.get("OPENAI_API_KEY")
    if not valeur and FICHIER_ENV.exists():
        for ligne in FICHIER_ENV.read_text(encoding="utf-8").splitlines():
            if ligne.startswith("OPENAI_API_KEY="):
                valeur = ligne.split("=", 1)[1].strip().strip("\"'")
    if not valeur:
        raise RuntimeError(f"OPENAI_API_KEY absente : la définir dans {FICHIER_ENV}")
    return valeur
