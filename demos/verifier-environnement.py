"""Controle a lancer la veille : uv, cle API, et plans B disponibles."""
import json
import os
import shutil
import subprocess
import sys
from importlib.util import find_spec

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commun  # noqa: E402

MODULES = ["tiktoken", "openai", "langchain_openai", "langchain_chroma", "chromadb",
           "langchain_text_splitters", "rank_bm25", "snowballstemmer"]
UV = shutil.which("uv")
LANCEUR = "uv run" if UV else "python"

TOKENISATION = os.path.join(commun.RACINE, "j1", "demo1-tokenisation")
# Fichiers que tiktoken met en cache : le sha1 de l'URL de chaque encodage.
ENCODAGES = ["9b5ad71b2ce5302211f9c61530b329a4922fc6a4",   # cl100k_base
             "fb374d419588a4632f3f557e76b4b70aebbca790"]   # o200k_base
# Memes noms que PROMPTS dans generer_image.py, plus les compteurs.
IMAGES = os.path.join(commun.RACINE, "j2", "demo4-image", "sorties")
FICHIERS_IMAGE = ["1-prompt-court.png", "2-prompt-detaille.png", "infos.json"]


def tokenisation_prete():
    """Les deux encodages en cache, et le script qui tourne vraiment sans reseau."""
    cache = os.path.join(TOKENISATION, "cache-tiktoken")
    if not all(os.path.exists(os.path.join(cache, f)) for f in ENCODAGES):
        return False
    if UV:
        commande = [UV, "run", "--offline", "--quiet", "tokenisation.py", "test"]
    elif find_spec("tiktoken"):
        commande = [sys.executable, "tokenisation.py", "test"]
    else:
        return False
    return subprocess.run(commande, cwd=TOKENISATION,
                          capture_output=True).returncode == 0


def images_pretes():
    """Une generation interrompue apres la premiere image n'est pas un plan B."""
    return all(os.path.exists(os.path.join(IMAGES, f)) for f in FICHIERS_IMAGE)


def enregistree(dossier):
    return lambda: os.path.exists(
        os.path.join(commun.RACINE, dossier, "sortie-enregistree.json"))


def similarite_prete():
    """L'enregistrement doit contenir les trois modes, pour que tous se rejouent."""
    chemin = os.path.join(commun.RACINE, "j2", "demo3-similarite", "sortie-enregistree.json")
    if not os.path.exists(chemin):
        return False
    with open(chemin, encoding="utf-8") as f:
        return all(m in q for q in json.load(f)["questions"]
                   for m in ("hybride", "semantique", "lexicale"))


PLANS_B = [
    ("J1 demo 1 tokenisation", tokenisation_prete,
     'cd j1/demo1-tokenisation && {0} tokenisation.py "test" '
     '&& {0} tokenisation.py --enc o200k_base "test"'),
    ("J2 demo 1 appel API", enregistree("j2/demo1-appel-api"),
     "cd j2/demo1-appel-api && {0} appel_brut.py --live --enregistrer"),
    ("J2 demo 2 template", enregistree("j2/demo2-langchain-template"),
     "cd j2/demo2-langchain-template && {0} template_chain.py --live --enregistrer"),
    ("J2 demo 3 similarite", similarite_prete,
     "cd j2/demo3-similarite && {0} similarite.py --live --enregistrer"),
    ("J2 demo 4 image", images_pretes,
     "cd j2/demo4-image && {0} generer_image.py --live"),
]


print("\n%s\nCONTROLE DE L'ENVIRONNEMENT\n%s" % ("=" * 76, "=" * 76))

commun.bloc("Outils")
print("  python %d.%d.%d (%s)" % (sys.version_info[:3] + (sys.prefix,)))
if UV:
    print("  " + subprocess.run([UV, "--version"], capture_output=True,
                                text=True).stdout.strip())
else:
    print("  uv ABSENT : l'installer, https://docs.astral.sh/uv/")
absents = [m for m in MODULES if find_spec(m) is None]
if absents:
    print("  Modules manquants : %s" % ", ".join(absents))
    print("  -> une fois, a la racine de la formation : uv sync")
    print("     puis relancer : uv run verifier-environnement.py")
else:
    print("  Dependances des demos : toutes installees")
print("  OPENAI_API_KEY : %s" % ("definie" if commun.cle() else "ABSENTE"))

commun.bloc("Plans B")
manquants = []
for nom, pret, commande in PLANS_B:
    ok = pret()
    print("  %-26s %s" % (nom, "pret" if ok else "A PREPARER"))
    if not ok:
        manquants.append(commande.format(LANCEUR))
print()
if manquants:
    print("  %d demo(s) a preparer, avec le reseau, depuis le dossier demos :"
          % len(manquants))
    for commande in manquants:
        print("  " + commande)
else:
    print("  Tout est pret : les demos tiennent meme sans reseau.")
print()
