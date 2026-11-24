"""Lab 3 : retrouver les bons extraits.

Chaque fonction de recherche renvoie au plus k Extrait, du plus pertinent au
moins pertinent. Tests : uv run pytest -k etape3 (puis etape4).

Corrigé de référence.
"""
import re

import snowballstemmer
from rank_bm25 import BM25Okapi

from app.rag import reglages
from app.rag.indexer import Extrait, magasin, morceaux

_racine = snowballstemmer.stemmer("french")


def decouper(texte: str) -> list[str]:
    """Minuscules, mots, racines : « congés » et « congé » deviennent le même mot.

    Fourni. BM25 compare des chaînes, pas du sens : sans racinisation, les
    pluriels et les conjugaisons ne se rejoignent pas.
    """
    return _racine.stemWords(re.findall(r"\w+", texte.lower()))


# --- Étape 3 ------------------------------------------------------------------

def semantique(question: str, k: int = reglages.K) -> list[Extrait]:
    """Les k extraits les plus proches de la question par le sens."""
    documents = magasin().similarity_search(question, k=k)
    return [Extrait(id=d.metadata["id"], source=d.metadata["source"], texte=d.page_content)
            for d in documents]


# --- Étape 4 ------------------------------------------------------------------

def lexicale(question: str, k: int = reglages.K) -> list[Extrait]:
    """Les k extraits qui partagent le plus de mots rares avec la question (BM25).

    L'index est reconstruit à chaque appel : quelques dizaines de morceaux,
    aucun appel réseau, et une modification du corpus est prise en compte
    sans redémarrer.
    """
    extraits = morceaux()
    scores = BM25Okapi([decouper(e.texte) for e in extraits]).get_scores(decouper(question))
    ordre = sorted(range(len(extraits)), key=lambda i: scores[i], reverse=True)
    return [extraits[i] for i in ordre[:k]]


def fusionner(classements: list[list[str]], poids: list[float], c: float = 0) -> list[str]:
    """Fusion par rang réciproque de plusieurs classements d'identifiants."""
    notes: dict[str, float] = {}
    for classement, poids_classement in zip(classements, poids):
        for rang, identifiant in enumerate(classement, start=1):
            notes[identifiant] = notes.get(identifiant, 0.0) + poids_classement / (c + rang)
    return sorted(notes, key=lambda identifiant: notes[identifiant], reverse=True)


def hybride(question: str, k: int = reglages.K) -> list[Extrait]:
    """Sémantique et lexicale, fusionnées avec reglages.POIDS et reglages.C, tronquées à k.

    La fusion rend l'union des deux listes, jusqu'à 2k extraits : sans
    troncature, le modèle recevrait deux fois plus de contexte.
    """
    listes = [semantique(question, k), lexicale(question, k)]
    par_id = {e.id: e for liste in listes for e in liste}
    ordre = fusionner([[e.id for e in liste] for liste in listes], list(reglages.POIDS), reglages.C)
    return [par_id[identifiant] for identifiant in ordre[:k]]


MODES = {"semantique": semantique, "lexicale": lexicale, "hybride": hybride}
