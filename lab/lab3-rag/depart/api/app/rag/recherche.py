"""Lab 3 : retrouver les bons extraits.

Chaque fonction de recherche renvoie au plus k Extrait, du plus pertinent au
moins pertinent. Tests : uv run pytest -k etape3 (puis etape4).
"""
import re

import snowballstemmer

from app.rag import reglages
from app.rag.indexer import Extrait, magasin, morceaux  # noqa: F401  (pour vos fonctions)

_racine = snowballstemmer.stemmer("french")


def decouper(texte: str) -> list[str]:
    """Minuscules, mots, racines : « congés » et « congé » deviennent le même mot.

    Fourni. BM25 compare des chaînes, pas du sens : sans racinisation, les
    pluriels et les conjugaisons ne se rejoignent pas.
    """
    return _racine.stemWords(re.findall(r"\w+", texte.lower()))


# --- Étape 3 ------------------------------------------------------------------

def semantique(question: str, k: int = reglages.K) -> list[Extrait]:
    """Les k extraits les plus proches de la question par le sens.

    magasin().similarity_search(question, k=k) renvoie des documents LangChain :
    le texte est dans .page_content, l'identifiant et la source dans .metadata.
    """
    raise NotImplementedError("Étape 3 : semantique")


# --- Étape 4 ------------------------------------------------------------------

def lexicale(question: str, k: int = reglages.K) -> list[Extrait]:
    """Les k extraits qui partagent le plus de mots rares avec la question (BM25).

    Pas d'appel réseau : l'index se reconstruit en mémoire à partir de morceaux().
    from rank_bm25 import BM25Okapi ; BM25Okapi([decouper(e.texte) for e in ...])
    puis .get_scores(decouper(question)) donne un score par morceau.
    """
    raise NotImplementedError("Étape 4 : lexicale")


def fusionner(classements: list[list[str]], poids: list[float], c: float = 0) -> list[str]:
    """Fusion par rang réciproque de plusieurs classements d'identifiants.

    Un identifiant au rang r (le premier est au rang 1) dans le classement i
    reçoit poids[i] / (c + r). On additionne ses notes, on trie par note
    décroissante. Exemple : [["a", "b"], ["b", "c"]], poids [1, 1], c = 0
    donne b (1/2 + 1/1), a (1/1), c (1/2) : ["b", "a", "c"].
    """
    raise NotImplementedError("Étape 4 : fusionner")


def hybride(question: str, k: int = reglages.K) -> list[Extrait]:
    """Sémantique et lexicale, fusionnées avec reglages.POIDS et reglages.C, tronquées à k."""
    raise NotImplementedError("Étape 4 : hybride")


MODES = {"semantique": semantique, "lexicale": lexicale, "hybride": hybride}
