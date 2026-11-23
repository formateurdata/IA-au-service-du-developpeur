"""Mesure l'assistant sur le jeu de questions de référence (questions.json).

    uv run python -m app.rag.evaluer                        rappel des trois recherches
    uv run python -m app.rag.evaluer --reponses aucun       réponses du modèle seul
    uv run python -m app.rag.evaluer --reponses hybride     réponses avec la recherche hybride
    uv run python -m app.rag.evaluer --detail ...           le détail question par question

Rappel : sur les 10 questions qui ont une réponse dans le corpus, combien de
fois le bon document figure parmi les K extraits envoyés au modèle. Si la
recherche ne le trouve pas, le modèle ne peut pas répondre juste.

Réponses : une réponse est juste si elle contient l'information attendue ;
pour les 2 questions sans réponse dans le corpus, si c'est un refus. C'est une
correction automatique, donc une estimation : une réponse qui cite le bon
chiffre pour le contredire serait comptée juste. --detail permet de vérifier.
"""
import argparse
import json
import re
from pathlib import Path

from app.rag import reglages
from app.rag.assistant import REFUS, repondre
from app.rag.indexer import magasin
from app.rag.recherche import MODES

QUESTIONS = json.loads((Path(__file__).parent / "questions.json").read_text(encoding="utf-8"))


def mesurer_rappel(mode: str, detail: bool) -> str:
    chercher = MODES[mode]
    trouves, avec_reponse = 0, [q for q in QUESTIONS if q["source"]]
    for q in avec_reponse:
        sources = [e.source for e in chercher(q["question"], reglages.K)]
        trouve = q["source"] in sources
        trouves += trouve
        if detail:
            print(f"    {'oui' if trouve else 'NON'}  {q['question']}  ->  {', '.join(sources)}")
    return f"{trouves}/{len(avec_reponse)}"


def est_refus(reponse: str) -> bool:
    return REFUS.lower().rstrip(".") in reponse.lower()


def contient(reponse: str, attendu: str) -> bool:
    """L'attendu en mots entiers : « 2 heures » ne compte pas dans « 72 heures »,
    ni « 150 » dans « 1500 ». Les espaces insécables comptent comme des espaces."""
    texte = " ".join(reponse.split())
    return re.search(rf"(?<!\w){re.escape(attendu)}(?!\w)", texte, re.IGNORECASE) is not None


def mesurer_reponses(mode: str, detail: bool) -> str:
    justes = 0
    for q in QUESTIONS:
        reponse = repondre(q["question"], mode)["reponse"]
        if q["source"]:
            juste = any(contient(reponse, attendu) for attendu in q["attendu"])
        else:
            juste = est_refus(reponse)
        justes += juste
        if detail:
            print(f"    {'juste' if juste else 'FAUX '}  {q['question']}\n           {reponse}")
    return f"{justes}/{len(QUESTIONS)}"


def index_present() -> bool:
    """Chroma crée une collection vide si elle n'existe pas : la recherche renverrait
    alors zéro extrait, sans la moindre erreur. On vérifie avant de mesurer."""
    try:
        return bool(magasin().get(limit=1)["ids"])
    except RuntimeError as erreur:  # clé absente
        raise SystemExit(str(erreur))


def main() -> None:
    parametres = argparse.ArgumentParser(description=__doc__,
                                         formatter_class=argparse.RawDescriptionHelpFormatter)
    parametres.add_argument("--reponses", choices=["aucun", *MODES],
                            help="mesurer aussi les réponses du modèle dans ce mode")
    parametres.add_argument("--detail", action="store_true")
    args = parametres.parse_args()

    # Seuls le mode « aucun » et la recherche lexicale se passent de l'index vectoriel.
    if args.reponses not in ("aucun", "lexicale") and not index_present():
        raise SystemExit("Index vide : lancer d'abord uv run python -m app.rag.indexer")

    if args.reponses:
        print(f"Réponses ({args.reponses}), sur {len(QUESTIONS)} questions dont 2 sans réponse")
        try:
            print(f"  justes : {mesurer_reponses(args.reponses, args.detail)}")
        except NotImplementedError as erreur:
            print(f"  à écrire : {erreur}")
        return

    print(f"Rappel : le bon document parmi les {reglages.K} extraits (10 questions)")
    for mode in MODES:
        if args.detail:
            print(f"  {mode}")
        try:
            print(f"  {mode:<11} {mesurer_rappel(mode, args.detail)}")
        except NotImplementedError as erreur:
            print(f"  {mode:<11} à écrire ({erreur})")


if __name__ == "__main__":
    main()
