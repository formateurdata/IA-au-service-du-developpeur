"""Socle des demos.

Deux modes : par defaut le script rejoue une sortie figee lors de la
repetition (ni reseau, ni cle, ni dependance) ; avec --live il appelle
reellement le service, et --live --enregistrer fige la sortie.

Les scripts affichent des donnees, pas un discours : ce qu'il faut dire est
dans le README de chaque demo et dans les notes du presentateur.
"""
import argparse
import json
import os
import sys
from importlib.util import find_spec

RACINE = os.path.dirname(os.path.abspath(__file__))


def cmd(suffixe=""):
    """La commande a taper, avec le lanceur et le chemin reellement utilises."""
    return "%s %s%s" % ("uv run" if os.environ.get("UV") else "python",
                        sys.argv[0], suffixe)


def bloc(titre):
    print("\n-- %s %s" % (titre, "-" * max(0, 72 - len(titre))))


def cle():
    """Clé lue dans l'environnement, sinon dans demos/.env (guillemets admis)."""
    valeur = os.environ.get("OPENAI_API_KEY")
    fichier = os.path.join(RACINE, ".env")
    if not valeur and os.path.exists(fichier):
        for ligne in open(fichier, encoding="utf-8"):
            if ligne.startswith("OPENAI_API_KEY="):
                valeur = ligne.split("=", 1)[1].strip().strip("\"'")
    return valeur


def lancer(doc, reference, collecte, montre, deps=(), besoin_cle=True,
           options=None):
    """Squelette commun a toutes les demos.

    options : fonction qui ajoute des arguments propres a la demo ; collecte
    et montre recoivent alors les arguments lus.
    """
    p = argparse.ArgumentParser(description=doc.splitlines()[0])
    p.add_argument("--live", action="store_true", help="appeler le service")
    p.add_argument("--enregistrer", action="store_true", help="figer la sortie")
    if options:
        options(p)
    args = p.parse_args()
    afficher = (lambda d: montre(d, args)) if options else montre

    print("\n%s\n%s\n%s" % ("=" * 76, doc.splitlines()[0], "=" * 76))
    if not args.live:
        if not os.path.exists(reference):
            sys.exit("Aucune sortie figee. Lancer une fois avec le reseau :\n"
                     "    " + cmd(" --live --enregistrer"))
        return afficher(json.load(open(reference, encoding="utf-8")))

    absents = [m for m in deps if find_spec(m) is None]
    if absents:
        sys.exit("Modules absents : %s.\nUne fois, a la racine de la formation : uv sync\n"
                 "Puis : uv run %s --live" % (", ".join(absents), sys.argv[0]))
    if besoin_cle and not cle():
        sys.exit("OPENAI_API_KEY absente : copier .env.example vers .env.")

    donnees = collecte(args) if options else collecte()
    afficher(donnees)
    if args.enregistrer:
        json.dump(donnees, open(reference, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print("\nSortie figee dans %s" % os.path.basename(reference))
