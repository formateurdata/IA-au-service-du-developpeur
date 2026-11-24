"""Lab 0 : vérifie que le poste est prêt pour les labs, la veille de la formation.

    python3 verifier_prerequis.py                (Windows : py verifier_prerequis.py)
    python3 verifier_prerequis.py --installer    installe aussi les dépendances (formation et labs)
    python3 verifier_prerequis.py --tester-cle   vérifie aussi que la clé OpenAI répond

Bibliothèque standard uniquement : fonctionne avant toute installation.
"""
import os
import re
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

LAB = Path(__file__).resolve().parent
DEPARTS = [LAB / "lab1-copilot" / "depart", LAB / "lab2-generation" / "depart",
           LAB / "lab3-rag" / "depart", LAB / "lab4-agents" / "depart"]
# Les labs qui appellent OpenAI ; le lab 4 passe par le compte Copilot.
DEPARTS_AVEC_CLE = DEPARTS[1:3]

resultats = []


def noter(ok, intitule, conseil=""):
    resultats.append(ok)
    marque = {True: "OK  ", False: "NON ", None: "?   "}[ok]
    print(f"  [{marque}] {intitule}" + (f"\n           -> {conseil}" if conseil and ok is not True else ""))


def version(commande):
    chemin = shutil.which(commande[0])
    if not chemin:
        return None
    try:
        sortie = subprocess.run([chemin] + commande[1:], capture_output=True, text=True, timeout=20)
        return (sortie.stdout or sortie.stderr).strip()
    except (OSError, subprocess.TimeoutExpired):
        return None


def majeure(texte):
    trouve = re.search(r"(\d+)\.(\d+)", texte or "")
    return (int(trouve.group(1)), int(trouve.group(2))) if trouve else (0, 0)


def port_libre(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def cle_du_lab(api):
    """La clé telle que le lab la lira : l'environnement, sinon son propre api/.env.

    Chaque lab ne lit que son fichier : une clé posée dans le lab 2 ne sert pas au lab 3.
    Renvoie (clé, origine), ou (None, None) si la clé manque ou est restée « sk-... »."""
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"], "variable OPENAI_API_KEY"
    fichier = api / ".env"
    valeur = None
    if fichier.exists():
        for ligne in fichier.read_text(encoding="utf-8").splitlines():
            if ligne.startswith("OPENAI_API_KEY="):
                valeur = ligne.split("=", 1)[1].strip().strip("\"'")
    if valeur and len(valeur) > 20 and "..." not in valeur:
        return valeur, str(fichier.relative_to(LAB))
    return None, None


def tester_cle(cle):
    requete = urllib.request.Request("https://api.openai.com/v1/models",
                                     headers={"Authorization": f"Bearer {cle}"})
    try:
        with urllib.request.urlopen(requete, timeout=15) as reponse:
            return reponse.status == 200, ""
    except urllib.error.HTTPError as erreur:
        return False, f"l'API répond {erreur.code} (401 : clé invalide, 429 : quota)"
    except OSError as erreur:
        return False, f"réseau : {erreur}"


def installer():
    """uv sync à la racine (démos), puis uv sync et npm install dans chaque dossier
    de départ : rien à télécharger le jour J."""
    print("\nInstallation des dépendances de la formation et des labs")
    uv, npm = shutil.which("uv"), shutil.which("npm")
    if not (uv and npm):
        noter(False, "installation impossible", "installer d'abord uv et Node.js")
        return
    fini = subprocess.run([uv, "sync"], cwd=LAB.parent, capture_output=True, text=True)
    lignes = (fini.stderr or fini.stdout).strip().splitlines()
    noter(fini.returncode == 0, "formation (démos)", lignes[-1] if lignes else "échec sans message")
    for depart in DEPARTS:
        for commande, dossier in (([uv, "sync"], depart / "api"), ([npm, "install"], depart / "web")):
            if not dossier.exists():
                continue
            fini = subprocess.run(commande, cwd=dossier, capture_output=True, text=True)
            lignes = (fini.stderr or fini.stdout).strip().splitlines()
            noter(fini.returncode == 0, f"{depart.parent.name}/{dossier.name}",
                  lignes[-1] if lignes else "échec sans message")


def main():
    print("Vérification des prérequis des labs\n")

    noter(sys.version_info >= (3, 8), f"Python {sys.version.split()[0]} pour ce script")

    v = version(["uv", "--version"])
    noter(bool(v), f"uv : {v or 'absent'}", "installer uv : https://docs.astral.sh/uv/")

    v = version(["node", "--version"])
    noter(majeure(v) >= (20, 0), f"Node.js : {v or 'absent'} (20 ou plus)",
          "installer Node.js LTS : https://nodejs.org")

    v = version(["npm", "--version"])
    noter(bool(v), f"npm : {v or 'absent'}", "fourni avec Node.js")

    v = version(["git", "--version"])
    noter(bool(v), f"git : {v or 'absent'}", "installer git : https://git-scm.com")

    extensions = version(["code", "--list-extensions"])
    if extensions is None:
        noter(None, "VS Code : commande « code » introuvable, Copilot non vérifiable",
              "vérifier à la main que l'icône Copilot est active dans VS Code")
    else:
        noter(True, "VS Code installé")
        presentes = extensions.lower().split()
        if "github.copilot-chat" in presentes or "github.copilot" in presentes:
            noter(True, "extension GitHub Copilot")
        else:
            # Les versions récentes de VS Code intègrent Copilot sans extension visible.
            noter(None, "GitHub Copilot : à vérifier dans VS Code",
                  "icône Copilot active dans la barre d'état, compte GitHub connecté, "
                  "mode Agent disponible dans Copilot Chat")

    for port in (8000, 5173):
        noter(port_libre(port), f"port {port} libre",
              "un autre programme l'utilise : l'arrêter avant les labs")

    cles = []
    for depart in DEPARTS_AVEC_CLE:
        api = depart / "api"
        cle, origine = cle_du_lab(api)
        nom = depart.parent.name
        # La clé est donnée en séance : la veille, son absence n'est pas bloquante.
        etat = True if cle else (False if "--tester-cle" in sys.argv else None)
        noter(etat, f"clé OpenAI du {nom} ({origine or 'pas encore posée'})",
              f"donnée en séance : dans {api.relative_to(LAB)}, copier env.exemple en .env "
              "et coller la clé après OPENAI_API_KEY=")
        if cle and cle not in cles:
            cles.append(cle)
    if "--tester-cle" in sys.argv:
        for cle in cles:  # une seule fois si les deux labs ont la même clé
            ok, raison = tester_cle(cle)
            noter(ok, "la clé OpenAI répond", raison)

    if "--installer" in sys.argv:
        installer()

    manquants = resultats.count(False)
    print("\n" + ("Tout est prêt." if not manquants else
                  f"{manquants} point(s) à corriger avant la formation."))
    sys.exit(1 if manquants else 0)


if __name__ == "__main__":
    main()
