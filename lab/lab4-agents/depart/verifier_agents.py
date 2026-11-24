# /// script
# requires-python = ">=3.11"
# ///
"""Contrôle les profils de .github/agents/, étape par étape.

    uv run verifier_agents.py --etape 2     les trois spécialistes
    uv run verifier_agents.py --etape 3     les trois spécialistes et l'orchestrateur

Le contrôle porte sur la forme : en-tête, outils, visibilité, éléments cités.
Il ne juge pas la qualité des consignes : la trace des tickets la montre.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pilote  # noqa: E402

# Pour chaque agent : l'étape où il est écrit, sa visibilité dans le menu, les
# outils qu'il doit avoir, ceux qu'il ne doit pas avoir, et ce que ses
# consignes doivent citer.
REGLES = {
    pilote.DEV: {
        "etape": 2, "visible": False, "requis": {"read", "edit"}, "interdits": {"execute", "agent"},
        "cite": ["api/", "web/", "Pydantic", "AbortController"],
    },
    pilote.REDACTEUR: {
        "etape": 2, "visible": False, "requis": {"read", "edit"}, "interdits": {"execute", "agent"},
        "cite": ["api/", "web/", "pytest", "Vitest"],
    },
    pilote.TESTEUR: {
        "etape": 2, "visible": False, "requis": {"read", "execute"}, "interdits": {"edit", "agent"},
        "cite": ["executer_tests_api", "executer_tests_web", "uv run", "npm test",
                 "npm run typecheck"],
    },
    "orchestrateur": {
        "etape": 3, "visible": True, "requis": {"read", "search", "edit", "execute", "agent"},
        "interdits": set(),
        "cite": ["api/", "web/", "AGENTS.md", ".copilot-plans/", "uv run --script pilote.py",
                 "--approuve", "traces/"],
    },
}
LONGUEUR_MINIMALE = 400

resultats = []


def noter(ok, intitule, conseil=""):
    resultats.append(ok)
    print(f"    [{'OK ' if ok else 'NON'}] {intitule}"
          + (f"\n          -> {conseil}" if conseil and not ok else ""))


def controler(role, regle):
    print(f"\n  {role}")
    try:
        outils, corps = pilote.lire_profil(role)
    except (OSError, ValueError) as erreur:
        noter(False, "profil lisible et entièrement écrit", str(erreur))
        return
    noter(True, "profil lisible et entièrement écrit")
    entete = pilote.lire_entete((pilote.PROFILS / f"{role}.agent.md")
                                .read_text(encoding="utf-8-sig").split("---", 2)[1])
    description = entete.get("description")
    noter(isinstance(description, str) and len(description) >= 20,
          "description d'une phrase", "le menu des agents affiche cette phrase : décrivez le rôle")
    cache = str(entete.get("user-invocable", "")).lower() == "false"
    if regle["visible"]:
        noter(not cache, "visible dans le menu des agents",
              "c'est le seul agent que le demandeur choisit : retirez user-invocable: false")
    else:
        noter(cache, "absent du menu des agents",
              "seul l'orchestrateur le sollicite : ajoutez user-invocable: false à l'en-tête")
    bases = {outil.split("/")[0] for outil in outils}
    manquants = sorted(regle["requis"] - bases)
    noter(not manquants, f"outils indispensables : {', '.join(sorted(regle['requis']))}",
          f"manque : {', '.join(manquants)}")
    en_trop = sorted(regle["interdits"] & bases)
    if regle["interdits"]:
        noter(not en_trop, f"aucun outil réservé à un autre rôle ({', '.join(sorted(regle['interdits']))})",
              f"à retirer : {', '.join(en_trop)}")
    noter(len(corps) >= LONGUEUR_MINIMALE, "consignes développées",
          f"{len(corps)} caractères : chaque section doit dire quoi faire et quoi ne pas faire")
    texte = corps.casefold()
    absents = [element for element in regle["cite"] if element.casefold() not in texte]
    noter(not absents, f"cite : {', '.join(regle['cite'])}", f"absent : {', '.join(absents)}")


def main():
    analyseur = argparse.ArgumentParser(description=__doc__,
                                        formatter_class=argparse.RawDescriptionHelpFormatter)
    analyseur.add_argument("--etape", type=int, choices=(2, 3), required=True)
    etape = analyseur.parse_args().etape
    titre = {2: "les trois spécialistes", 3: "les trois spécialistes et l'orchestrateur"}[etape]
    print(f"Étape {etape} : {titre}")
    for role, regle in REGLES.items():
        if regle["etape"] <= etape:
            controler(role, regle)
    if all(resultats):
        try:
            pilote.verifier_profils()
        except (OSError, ValueError) as erreur:
            noter(False, "profils acceptés par le pilote", str(erreur))
    manquants = resultats.count(False)
    print("\n" + (f"Étape {etape} terminée." if not manquants
                  else f"{manquants} point(s) à corriger."))
    return 1 if manquants else 0


if __name__ == "__main__":
    sys.exit(main())
