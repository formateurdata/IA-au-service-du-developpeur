"""Mesure la conformité de la génération sur plusieurs appels réels.

    uv run python -m app.mesurer libre
    uv run python -m app.mesurer structure
    uv run python -m app.mesurer structure --appels 3
    uv run python -m app.mesurer libre --description "Une carte pour..."

Chaque HTML reçu est écrit tel quel dans sortie/, à ouvrir dans un navigateur.
Une politique de sécurité placée en tête y bloque scripts et ressources externes :
on voit la sortie du modèle sans lui donner le moindre droit.
"""
import argparse
from collections import Counter
from pathlib import Path

from app.config import cout_usd
from app.generation import controler, generer_libre, generer_structure

DESCRIPTION = ("Carte de bienvenue pour Camille Martin, développeuse, qui rejoint l'équipe "
               "Data le 1er décembre. Son référent est Karim Benali. Ajouter trois boutons : "
               "Écrire à Camille, Voir l'équipe, Planifier un café.")

SORTIE = Path(__file__).resolve().parent.parent / "sortie"

# Ni script, ni attribut d'événement, ni iframe, ni ressource externe ; le CSS
# en ligne reste permis, pour que la carte s'affiche comme elle a été écrite.
PROTECTION = ('<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
              'style-src \'unsafe-inline\'; img-src data:">')


def protege(html: str) -> str:
    """Place PROTECTION en tête du document, après le <!DOCTYPE> s'il y en a un."""
    debut = html.lstrip()
    if debut.lower().startswith("<!doctype"):
        fin = debut.index(">") + 1
        return debut[:fin] + PROTECTION + debut[fin:]
    return PROTECTION + "\n" + html


def main() -> None:
    parametres = argparse.ArgumentParser(description=__doc__,
                                         formatter_class=argparse.RawDescriptionHelpFormatter)
    parametres.add_argument("mode", choices=["libre", "structure"])
    parametres.add_argument("--appels", type=int, default=5)
    parametres.add_argument("--description", default=DESCRIPTION)
    args = parametres.parse_args()

    generer = generer_libre if args.mode == "libre" else generer_structure
    SORTIE.mkdir(exist_ok=True)
    conformes, echecs, cout_total = 0, Counter(), 0.0
    print(f"Mode {args.mode}, {args.appels} appels\nDescription : {args.description}\n")
    for numero in range(1, args.appels + 1):
        resultat = generer(args.description)
        controles = controler(resultat.html)
        tenus = sum(controles.values())
        cout = cout_usd(resultat.tokens_entree, resultat.tokens_sortie)
        cout_total += cout
        conformes += tenus == len(controles)
        echecs.update(nom for nom, ok in controles.items() if not ok)
        fichier = SORTIE / f"{args.mode}-{numero}.html"
        fichier.write_text(protege(resultat.html), encoding="utf-8")
        print(f"  appel {numero} : {tenus}/{len(controles)} contrôles, "
              f"{len(resultat.html)} caractères, {resultat.tokens_entree} + "
              f"{resultat.tokens_sortie} tokens, {cout:.5f} $  -> sortie/{fichier.name}")
    print(f"\nConformes au format : {conformes}/{args.appels}    "
          f"Coût total : {cout_total:.4f} $")
    for nom, nombre in echecs.most_common():
        print(f"  non tenu {nombre} fois : {nom}")


if __name__ == "__main__":
    main()
