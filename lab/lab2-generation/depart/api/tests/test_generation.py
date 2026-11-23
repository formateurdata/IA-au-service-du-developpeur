"""Lab 2 : tests de la génération, sans réseau ni clé.

Un faux client remplace OpenAI : il enregistre ce qu'on lui envoie et renvoie
une réponse préparée. Lancer une étape à la fois :

    uv run pytest -k etape1
"""
from types import SimpleNamespace

import openai
import pytest

from app import config, generation
from app.generation import CHARGE_INJECTION, CarteHTML

try:
    import httpx2 as _http
except ImportError:  # anciennes versions du SDK
    import httpx as _http

DESCRIPTION = "Carte de bienvenue pour Camille Martin, développeuse, équipe Data."
URL = "https://api.openai.com/v1/responses"


class FauxClient:
    """Imite client.responses.create et client.responses.parse."""

    def __init__(self, texte="<div>Bienvenue Camille</div>", carte=None, erreur=None):
        self.texte = texte
        self.carte = carte or CarteHTML(html='<div class="carte">Bienvenue Camille</div>',
                                        css=".carte { border-radius: 8px; }")
        self.erreur = erreur
        self.appels: list[tuple[str, dict]] = []
        self.responses = self

    def _usage(self):
        return SimpleNamespace(input_tokens=120, output_tokens=380)

    def create(self, **arguments):
        self.appels.append(("create", arguments))
        if self.erreur:
            raise self.erreur
        return SimpleNamespace(output_text=self.texte, usage=self._usage())

    def parse(self, **arguments):
        self.appels.append(("parse", arguments))
        if self.erreur:
            raise self.erreur
        return SimpleNamespace(output_parsed=self.carte, usage=self._usage())


@pytest.fixture
def faux(monkeypatch):
    client = FauxClient()
    monkeypatch.setattr(generation, "client", lambda: client)
    return client


# --- Étape 1 : la génération libre ----------------------------------------------

def test_etape1_envoie_la_description_telle_quelle(faux):
    generation.generer_libre(DESCRIPTION)
    methode, arguments = faux.appels[0]
    assert methode == "create"
    assert arguments["input"] == DESCRIPTION
    assert arguments["model"] == config.MODELE
    assert not arguments.get("instructions"), "pas de prompt système en mode libre"


def test_etape1_renvoie_le_texte_et_les_tokens(faux):
    resultat = generation.generer_libre(DESCRIPTION)
    assert resultat.html == faux.texte
    assert (resultat.tokens_entree, resultat.tokens_sortie) == (120, 380)


# --- Étape 2 : la génération structurée -------------------------------------------

def test_etape2_impose_le_format_par_le_prompt_systeme(faux):
    generation.generer_structure(DESCRIPTION)
    methode, arguments = faux.appels[0]
    assert methode == "parse"
    assert arguments["text_format"] is CarteHTML
    assert len(arguments.get("instructions") or "") >= 80, "SYSTEME est trop court ou absent"
    assert arguments.get("temperature") == 0


def test_etape2_ne_repete_pas_les_consignes_dans_la_demande(faux):
    generation.generer_structure(DESCRIPTION)
    assert faux.appels[0][1]["input"] == DESCRIPTION


def test_etape2_assemble_une_seule_balise_style(faux):
    resultat = generation.generer_structure(DESCRIPTION)
    assert resultat.html.lstrip().startswith("<style>")
    assert resultat.html.count("<style>") == 1
    assert faux.carte.css in resultat.html
    assert faux.carte.html in resultat.html
    assert all(generation.controler(resultat.html).values())


# --- Étape 3 : l'assainissement ---------------------------------------------------

def test_etape3_retire_les_vecteurs_d_injection():
    propre = generation.assainir(CHARGE_INJECTION).lower()
    for vecteur in ("onerror", "onload", "javascript:", "<iframe"):
        assert vecteur not in propre, vecteur
    assert "texte légitime à conserver." in propre


def test_etape3_garde_le_html_legitime():
    legitime = ('<style>.carte { border-radius: 8px; }</style>'
                '<div class="carte" id="camille"><img src="photo.png" alt="Camille">'
                '<h2>Bienvenue</h2><button>Écrire à Camille</button></div>')
    propre = generation.assainir(legitime)
    for attendu in (".carte { border-radius: 8px; }", 'class="carte"', 'id="camille"',
                    "<button>Écrire à Camille</button>", 'alt="Camille"'):
        assert attendu in propre, attendu


def test_etape3_la_route_renvoie_du_html_assaini(client, faux):
    faux.texte = CHARGE_INJECTION
    reponse = client.post("/api/cartes", json={"description": DESCRIPTION, "mode": "libre"})
    assert reponse.status_code == 200
    assert "onerror" not in reponse.json()["html"]


# --- Étape 4 : robustesse et coût -------------------------------------------------

def test_etape4_le_client_a_un_delai_et_des_reessais(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    c = config.client()
    secondes = c.timeout if isinstance(c.timeout, (int, float)) else c.timeout.read
    assert secondes is not None and secondes <= 30, "délai par défaut : 10 minutes"
    assert c.max_retries >= 1


def test_etape4_delai_depasse_renvoie_504(client, faux):
    faux.erreur = openai.APITimeoutError(request=_http.Request("POST", URL))
    reponse = client.post("/api/cartes", json={"description": DESCRIPTION})
    assert reponse.status_code == 504
    assert "réessayez" in reponse.json()["detail"].lower()


def test_etape4_trop_de_requetes_renvoie_503_sans_fuite(client, faux):
    requete = _http.Request("POST", URL)
    faux.erreur = openai.RateLimitError(
        "Rate limit reached for sk-test-SECRET in organization org-INTERNE",
        response=_http.Response(429, request=requete), body=None)
    reponse = client.post("/api/cartes", json={"description": DESCRIPTION})
    assert reponse.status_code == 503
    assert "SECRET" not in reponse.text and "org-" not in reponse.text


def test_etape4_la_route_renvoie_le_cout(client, faux):
    corps = client.post("/api/cartes", json={"description": DESCRIPTION}).json()
    assert corps["cout_usd"] == pytest.approx(config.cout_usd(120, 380))
