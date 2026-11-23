"""Lab 3 : tests du RAG, sans réseau ni clé.

Les vecteurs sont calculés par un faux modèle d'embedding, déterministe : il
ne comprend rien au sens, mais il permet de vérifier la mécanique. La
pertinence réelle se mesure avec evaluer.py, sur le vrai modèle.

    uv run pytest -k etape3
"""
import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.rag import assistant, indexer, recherche, reglages
from app.rag.indexer import Extrait

SOURCES = {f.stem for f in reglages.CORPUS.glob("*.txt")}


@pytest.fixture
def base_de_test(tmp_path, monkeypatch):
    """Une base Chroma temporaire, remplie avec de faux vecteurs."""
    faux = DeterministicFakeEmbedding(size=64)
    monkeypatch.setattr(reglages, "BASE", tmp_path / "chroma")
    monkeypatch.setattr(indexer, "embeddings", lambda: faux)
    indexer.indexer(faux)
    return faux


# --- Fourni : l'indexation --------------------------------------------------------

def test_indexation_sans_doublon(base_de_test):
    attendu = len(indexer.morceaux())
    indexer.indexer(base_de_test)  # une seconde fois : la collection est remise à zéro
    assert len(indexer.magasin(base_de_test).get()["ids"]) == attendu


# --- Étape 3 : recherche sémantique et réponse --------------------------------------

def test_etape3_semantique_renvoie_k_extraits(base_de_test):
    extraits = recherche.semantique("Combien de jours de télétravail ?", k=3)
    assert len(extraits) == 3
    assert all(isinstance(e, Extrait) for e in extraits)
    assert all(e.source in SOURCES and e.id.startswith(e.source) for e in extraits)
    assert all(e.texte for e in extraits)


@pytest.fixture
def modele_espion(monkeypatch):
    """Remplace le modèle : enregistre le prompt, renvoie une réponse préparée."""
    espion = {"reponse": "Trois jours par semaine au maximum."}

    def appeler(systeme, utilisateur):
        espion["systeme"], espion["utilisateur"] = systeme, utilisateur
        return espion["reponse"]

    monkeypatch.setattr(assistant, "appeler_modele", appeler)
    extraits = [Extrait("teletravail#0", "teletravail", "Trois jours par semaine au maximum."),
                Extrait("teletravail#1", "teletravail", "Les mardis sont sur site."),
                Extrait("conges#0", "conges", "25 jours ouvrés par an.")]
    monkeypatch.setitem(assistant.MODES, "semantique", lambda question, k=3: extraits)
    return espion


def test_etape3_les_extraits_et_leur_source_sont_dans_le_prompt(modele_espion):
    assistant.repondre("Combien de jours de télétravail ?", "semantique")
    message = modele_espion["utilisateur"]
    assert "Combien de jours de télétravail ?" in message
    assert "Trois jours par semaine au maximum." in message
    assert "25 jours ouvrés par an." in message
    assert "teletravail" in message and "conges" in message


def test_etape3_le_prompt_systeme_impose_le_refus(modele_espion):
    assistant.repondre("Combien de jours de télétravail ?", "semantique")
    assert assistant.REFUS in modele_espion["systeme"]


def test_etape3_sources_sans_doublon_dans_l_ordre(modele_espion):
    resultat = assistant.repondre("Combien de jours de télétravail ?", "semantique")
    assert resultat["reponse"] == "Trois jours par semaine au maximum."
    assert resultat["sources"] == ["teletravail", "conges"]


def test_etape3_un_refus_ne_cite_aucune_source(modele_espion):
    modele_espion["reponse"] = assistant.REFUS
    assert assistant.repondre("Prime de cooptation ?", "semantique")["sources"] == []


# --- Étape 4 : recherche lexicale et fusion ------------------------------------------

def test_etape4_lexicale_trouve_un_identifiant_exact():
    extraits = recherche.lexicale("Que dit la procédure PR-045 ?", k=3)
    assert len(extraits) == 3
    assert extraits[0].source == "astreinte"


def test_etape4_lexicale_rapproche_les_formes_d_un_mot():
    assert recherche.lexicale("congé enfant malade", k=1)[0].source == "conges"


def test_etape4_fusion_par_rang_reciproque():
    classements = [["a", "b", "c"], ["c", "a", "d"]]
    assert recherche.fusionner(classements, [1, 1], c=0) == ["a", "c", "b", "d"]
    assert recherche.fusionner(classements, [0.3, 0.7], c=0) == ["c", "a", "d", "b"]


def test_etape4_la_constante_c_aplatit_les_rangs():
    # c est troisième des deux listes ; a et d sont chacun premier d'une seule.
    classements = [["a", "b", "c"], ["d", "e", "c"]]
    # Avec c = 0, être premier quelque part l'emporte.
    assert recherche.fusionner(classements, [1, 1], c=0)[:2] in (["a", "d"], ["d", "a"])
    # Avec c = 60, 1/61 et 1/63 sont presque égaux : être présent deux fois,
    # même mal classé, l'emporte. C'est la valeur par défaut de LangChain.
    assert recherche.fusionner(classements, [1, 1], c=60)[0] == "c"


def test_etape4_hybride_tronque_a_k_et_garde_l_identifiant_exact(base_de_test):
    extraits = recherche.hybride("Que dit la procédure PR-045 ?", k=3)
    assert len(extraits) == 3
    assert len({e.id for e in extraits}) == 3
    assert "astreinte" in {e.source for e in extraits}
