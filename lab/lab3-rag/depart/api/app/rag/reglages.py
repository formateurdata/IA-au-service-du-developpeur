"""Les réglages du RAG. Ce sont eux que vous ferez varier au défi de fin de lab."""
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
CORPUS = DOSSIER / "corpus"
BASE = DOSSIER.parent.parent / "chroma_db"     # api/chroma_db, recréé par l'indexation
COLLECTION = "procedures"

EMBEDDING = "text-embedding-3-small"   # changer de modèle impose de réindexer
TAILLE_MORCEAU = 800                   # caractères par morceau
CHEVAUCHEMENT = 100                    # caractères repris d'un morceau au suivant
K = 3                                  # extraits envoyés au modèle

# Fusion hybride : poids (sémantique, lexicale) et constante c du rang réciproque.
POIDS = (0.3, 0.7)
C = 0
