"""Indexation du corpus : découper, calculer un vecteur par morceau, stocker.

    uv run python -m app.rag.indexer

Fourni : c'est le temps « hors ligne » du RAG, fait une fois, et refait à
chaque modification du corpus ou des réglages de découpage.
"""
import os
from dataclasses import dataclass

from app.config import cle
from app.rag import reglages

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")  # Chroma n'envoie rien


@dataclass(frozen=True)
class Extrait:
    """Un morceau de procédure : son identifiant, son document d'origine, son texte."""

    id: str
    source: str
    texte: str


def morceaux() -> list[Extrait]:
    """Le corpus découpé. Les recherches sémantique et lexicale voient les mêmes morceaux."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    decoupeur = RecursiveCharacterTextSplitter(chunk_size=reglages.TAILLE_MORCEAU,
                                               chunk_overlap=reglages.CHEVAUCHEMENT)
    extraits = []
    for fichier in sorted(reglages.CORPUS.glob("*.txt")):
        for numero, texte in enumerate(decoupeur.split_text(fichier.read_text(encoding="utf-8"))):
            extraits.append(Extrait(id=f"{fichier.stem}#{numero}", source=fichier.stem, texte=texte))
    return extraits


def embeddings():
    """Le modèle qui transforme un texte en vecteur. Le même à l'indexation et à la recherche."""
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(model=reglages.EMBEDDING, api_key=cle())


def magasin(fonction_embeddings=None):
    """La base vectorielle Chroma, stockée dans api/chroma_db."""
    from langchain_chroma import Chroma

    return Chroma(collection_name=reglages.COLLECTION,
                  embedding_function=fonction_embeddings or embeddings(),
                  persist_directory=str(reglages.BASE))


def indexer(fonction_embeddings=None) -> int:
    """Vide la collection et la remplit à nouveau. Renvoie le nombre de morceaux.

    Si le calcul des vecteurs échoue (réseau, quota), la collection reste vide :
    relancer l'indexation une fois le fournisseur revenu."""
    fonction = fonction_embeddings or embeddings()
    # Sans cette remise à zéro, une nouvelle indexation ajouterait les morceaux
    # une seconde fois, et les mêmes extraits remonteraient en double.
    magasin(fonction).delete_collection()
    extraits = morceaux()
    magasin(fonction).add_texts(texts=[e.texte for e in extraits],
                                metadatas=[{"id": e.id, "source": e.source} for e in extraits],
                                ids=[e.id for e in extraits])
    return len(extraits)


if __name__ == "__main__":
    nombre_fichiers = len(list(reglages.CORPUS.glob("*.txt")))
    print(f"{indexer()} morceaux indexés depuis {nombre_fichiers} fichiers, dans {reglages.BASE}")
