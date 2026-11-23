"""Lab 2 : la carte de bienvenue d'un nouvel arrivant, générée par un modèle.

L'utilisateur décrit la carte, le modèle renvoie du HTML et du CSS, la page
l'affiche. Quatre étapes, une par fonction marquée « À écrire » :

    1. generer_libre      la description, telle quelle, au modèle
    2. generer_structure  un prompt système et une sortie au format imposé
    3. assainir           nettoyer le HTML avant de le renvoyer
    4. creer_carte        délai dépassé, erreurs du fournisseur, coût

Les tests de chaque étape : uv run pytest -k etape1 (puis etape2, ...).
"""
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import MODELE, client, cout_usd  # noqa: F401  (cout_usd sert à l'étape 4)

routeur = APIRouter()


# --- Fourni -------------------------------------------------------------------

class CarteHTML(BaseModel):
    """Le format imposé au modèle à l'étape 2."""

    html: str = Field(description="Le HTML de la carte, sans balise <style> ni <script>")
    css: str = Field(description="Le CSS de la carte, sans balise <style> autour")


@dataclass
class Resultat:
    """Ce que renvoie une génération : le HTML et les tokens consommés."""

    html: str
    tokens_entree: int
    tokens_sortie: int


# Les vecteurs réels d'une injection sont les attributs d'événement, les liens
# javascript: et les <iframe>. Une balise <script> insérée par innerHTML n'est
# pas exécutée : la retirer seule ne protégerait de rien.
CHARGE_INJECTION = (
    '<img src="photo.png" onerror="alert(\'intrusion par onerror\')"'
    ' onload="alert(\'intrusion par onload\')">\n'
    '<a href="javascript:alert(\'intrusion par lien\')">Voir le profil</a>\n'
    '<iframe src="https://malveillant.example/piege"></iframe>\n'
    '<p>Texte légitime à conserver.</p>'
)

ELEMENTS_VIDES = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
                  "source", "track", "wbr"}


class _Balises(HTMLParser):
    """Compte les balises ouvertes et jamais fermées, ou fermées sans avoir été ouvertes."""

    def __init__(self):
        super().__init__()
        self.pile: list[str] = []
        self.erreurs = 0

    def handle_starttag(self, tag, attrs):
        if tag not in ELEMENTS_VIDES:
            self.pile.append(tag)

    def handle_endtag(self, tag):
        if tag in ELEMENTS_VIDES:
            return
        if self.pile and self.pile[-1] == tag:
            self.pile.pop()
        else:
            self.erreurs += 1


def controler(html: str) -> dict[str, bool]:
    """Contrôles mécaniques du HTML reçu, affichés dans la page et par mesurer.py.

    Ce sont des contrôles de forme, pas une protection : une <iframe>, ou un CSS
    qui masque toute la page, peuvent les passer tous les six.
    """
    analyse = _Balises()
    analyse.feed(html)
    analyse.close()
    bas = html.lower()
    return {
        "Aucun texte avant la première balise": html.lstrip().startswith("<"),
        "Pas de bloc de code markdown": "```" not in html,
        "Une seule balise <style>": bas.count("<style") == 1,
        "Aucune balise <script>": "<script" not in bas,
        "Aucun attribut d'événement": re.search(r"<[^>]+\son[a-z]+\s*=", bas) is None,
        "Balises bien fermées": analyse.erreurs == 0 and not analyse.pile,
    }


# --- À écrire -----------------------------------------------------------------

# Étape 2 : les consignes de format, envoyées en prompt système.
SYSTEME = ""


def generer_libre(description: str) -> Resultat:
    """Étape 1 : envoie la description seule, sans prompt système, température par défaut.

    Utiliser client().responses.create(model=MODELE, input=...) ; le texte
    produit est dans .output_text, les tokens dans .usage.
    """
    raise NotImplementedError("Étape 1 : generer_libre")


def generer_structure(description: str) -> Resultat:
    """Étape 2 : SYSTEME en prompt système, température 0, sortie au format CarteHTML.

    Utiliser client().responses.parse(..., text_format=CarteHTML) ; la carte
    est dans .output_parsed. Assembler le CSS dans une seule balise <style>,
    suivie du HTML.
    """
    raise NotImplementedError("Étape 2 : generer_structure")


def assainir(html: str) -> str:
    """Étape 3 : retire tout ce qui peut exécuter du code, garde le reste.

    Avec nh3, une bibliothèque éprouvée. Jamais d'expression régulière.
    """
    raise NotImplementedError("Étape 3 : assainir")


class DemandeCarte(BaseModel):
    description: str = Field(min_length=10, max_length=1000)
    mode: Literal["libre", "structure"] = "libre"


@routeur.post("/api/cartes")
def creer_carte(demande: DemandeCarte):
    """Génère une carte. Étapes 3 et 4 : à compléter."""
    generer = generer_libre if demande.mode == "libre" else generer_structure
    resultat = generer(demande.description)
    html = resultat.html
    return {
        "html": html,
        "controles": controler(html),
        "tokens_entree": resultat.tokens_entree,
        "tokens_sortie": resultat.tokens_sortie,
    }
