"""Réglages partagés : la clé, le modèle, le prix des tokens."""
import os
from pathlib import Path

RACINE_API = Path(__file__).resolve().parent.parent
FICHIER_ENV = RACINE_API / ".env"

MODELE = "gpt-4o-mini"

# Prix publics du modèle, en dollars par million de tokens. À vérifier sur
# la page de tarifs du fournisseur avant la session.
PRIX_ENTREE_USD = 0.15
PRIX_SORTIE_USD = 0.60


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


def client():
    """Le client OpenAI du portail."""
    from openai import OpenAI

    return OpenAI(api_key=cle())


def cout_usd(tokens_entree: int, tokens_sortie: int) -> float:
    """Le coût d'un appel, en dollars."""
    return (tokens_entree * PRIX_ENTREE_USD + tokens_sortie * PRIX_SORTIE_USD) / 1_000_000
