"""Lab 3 : répondre à partir des extraits retrouvés.

Tests : uv run pytest -k etape3
"""
from app.config import MODELE, cle
from app.rag.recherche import MODES

# La phrase exacte attendue quand les procédures ne contiennent pas la réponse.
# evaluer.py la cherche pour compter les refus corrects.
REFUS = "Je ne trouve pas cette information dans les procédures."

SANS_DOCUMENT = "Tu es l'assistant RH de l'entreprise. Réponds en une ou deux phrases."


def appeler_modele(systeme: str, utilisateur: str) -> str:
    """Fourni : un appel au modèle de conversation, à température 0."""
    from langchain_openai import ChatOpenAI

    modele = ChatOpenAI(model=MODELE, temperature=0, api_key=cle(), timeout=30, max_retries=2)
    return modele.invoke([("system", systeme), ("human", utilisateur)]).content


def repondre(question: str, mode: str = "hybride") -> dict:
    """Renvoie {"reponse": texte, "sources": [documents transmis au modèle]}.

    mode "aucun" : le modèle seul, sans document. Fourni : c'est la référence.
    Les autres modes : à écrire à l'étape 3.
    """
    if mode == "aucun":
        return {"reponse": appeler_modele(SANS_DOCUMENT, question), "sources": []}

    # Étape 3 :
    # 1. extraits = MODES[mode](question)
    # 2. un prompt système qui impose de répondre uniquement à partir des
    #    extraits, et de répondre exactement REFUS sinon ;
    # 3. les extraits et la question dans le message utilisateur, chaque
    #    extrait précédé du nom de son document ;
    # 4. sources : les documents des extraits, sans doublon, dans l'ordre ;
    #    aucune source si la réponse est un refus.
    raise NotImplementedError("Étape 3 : repondre")
