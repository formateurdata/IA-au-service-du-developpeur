"""Jour 2 - Demo 2 : prompt template et chaine

Un gabarit ecrit une fois, trois jeux de parametres : le message d'accueil de
la carte de bienvenue, celle que le Lab 2 fait generer. Les appels 1 et 2 ne
different que par le ton, les appels 1 et 3 que par la personne. Le script
affiche le prompt reellement envoye a chaque appel. Voir README.md.

    uv run template_chain.py --live --enregistrer   # avant la session
    python3 template_chain.py                       # le jour J (rejeu)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import commun  # noqa: E402

REF = os.path.join(os.path.dirname(__file__), "sortie-enregistree.json")
MODELE = "gpt-4o-mini"
GABARIT = (
    "Rédige en deux phrases le message d'accueil de la carte de bienvenue "
    "d'un nouvel arrivant.\n"
    "Ton : {ton}.\nPrénom : {prenom}\nPoste : {poste}\nÉquipe : {equipe}"
)
JEUX = [
    {
        "prenom": "Camille",
        "poste": "développeuse back-end",
        "equipe": "Portail interne",
        "ton": "chaleureux",
    },
    {
        "prenom": "Camille",
        "poste": "développeuse back-end",
        "equipe": "Portail interne",
        "ton": "sobre et professionnel",
    },
    {
        "prenom": "Yanis",
        "poste": "alternant en analyse de données",
        "equipe": "Pilotage",
        "ton": "chaleureux",
    },
]


def collecte():
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    # Le gabarit et le modele sont assembles une fois : c'est la chaine. Seuls
    # les parametres changent ensuite, jamais le texte du prompt.
    chaine = ChatPromptTemplate.from_template(GABARIT) | ChatOpenAI(
        model=MODELE, temperature=0, api_key=commun.cle())
    return {"resultats": [{"parametres": jeu, "reponse": chaine.invoke(jeu).content}
                          for jeu in JEUX]}


def montre(donnees):
    commun.bloc("Gabarit, écrit une seule fois")
    print(GABARIT)
    for numero, r in enumerate(donnees["resultats"], 1):
        jeu = r["parametres"]
        commun.bloc("Appel %d : %s, ton %s" % (numero, jeu["prenom"], jeu["ton"]))
        print("  prompt envoyé :")
        print("    " + GABARIT.format(**jeu).replace("\n", "\n    "))
        print("  réponse :")
        print("    " + r["reponse"].replace("\n", "\n    "))


if __name__ == "__main__":
    commun.lancer(__doc__, REF, collecte, montre,
                  deps=("langchain_core", "langchain_openai"))
