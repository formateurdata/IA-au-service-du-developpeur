"""Jour 2 - Demo 1 : appel API brut

Affiche la requete minimale et la reponse non mise en forme, avec la meme API
que le Lab 2 (responses). L'interet est dans les metadonnees : le bloc usage,
le cout de l'appel, et le statut d'une reponse coupee. Voir README.md.

    uv run appel_brut.py --live --enregistrer   # avant la session
    python3 appel_brut.py                       # le jour J (rejeu)
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import commun  # noqa: E402

REF = os.path.join(os.path.dirname(__file__), "sortie-enregistree.json")
MODELE = "gpt-4o-mini"
# Memes prix que lab/lab2-generation/depart/api/app/config.py, en dollars par
# million de tokens. A verifier sur la page des tarifs avant la session.
PRIX_ENTREE_USD = 0.15
PRIX_SORTIE_USD = 0.60
INSTRUCTIONS = "Tu es concis. Trois phrases maximum."
QUESTION = ("Explique à un développeur ce qu'est la fenêtre de contexte "
            "d'un modèle de langage.")
# Le minimum accepte par l'API : assez court pour couper la reponse.
LIMITE_COURTE = 16


def collecte():
    from openai import OpenAI
    client = OpenAI(api_key=commun.cle())
    appel = {"model": MODELE, "instructions": INSTRUCTIONS, "input": QUESTION}
    return {
        "complet": client.responses.create(**appel).model_dump(mode="json"),
        "coupe": client.responses.create(
            **appel, max_output_tokens=LIMITE_COURTE).model_dump(mode="json"),
    }


def texte(reponse):
    """Le texte produit, que le SDK expose aussi sous reponse.output_text."""
    return "".join(contenu.get("text", "")
                   for element in reponse.get("output") or []
                   if element.get("type") == "message"
                   for contenu in element.get("content") or []
                   if contenu.get("type") == "output_text")


def cout(usage):
    return (usage["input_tokens"] * PRIX_ENTREE_USD
            + usage["output_tokens"] * PRIX_SORTIE_USD) / 1_000_000


def montre(donnees):
    commun.bloc("Requête envoyée")
    print(json.dumps({"model": MODELE, "instructions": INSTRUCTIONS,
                      "input": QUESTION}, ensure_ascii=False, indent=2))

    reponse = donnees["complet"]
    commun.bloc("Réponse brute (champs vides retirés)")
    remplis = {cle: valeur for cle, valeur in reponse.items()
               if valeur not in (None, [], {}, "")}
    print(json.dumps(remplis, ensure_ascii=False, indent=2)[:2500])

    usage = reponse["usage"]
    commun.bloc("Ce qu'il faut regarder")
    print("  texte  : %s" % texte(reponse))
    print("  tokens : entrée %s + sortie %s = %s facturés"
          % (usage["input_tokens"], usage["output_tokens"], usage["total_tokens"]))
    print("  coût   : %.6f $ l'appel, %.2f $ les 1 000 appels"
          % (cout(usage), cout(usage) * 1000))
    print("  status : %s" % reponse["status"])

    coupe = donnees["coupe"]
    raison = (coupe.get("incomplete_details") or {}).get("reason")
    commun.bloc("Le même appel, avec max_output_tokens=%d" % LIMITE_COURTE)
    print("  texte  : %s" % texte(coupe))
    print("  status : %s   raison : %s" % (coupe["status"], raison))
    print("  completed = terminé ; incomplete = coupé. À tester avant d'utiliser le texte.")


if __name__ == "__main__":
    commun.lancer(__doc__, REF, collecte, montre, deps=("openai",))
