# /// script
# requires-python = ">=3.11"
# dependencies = ["microsoft-copilot-sdk==2.0.1"]
# ///
"""Pilote les trois spécialistes après validation du plan par l'orchestrateur VS Code.

    uv run --script pilote.py --plan .copilot-plans/x.json      montre le plan et demande l'accord
    uv run --script pilote.py --plan .copilot-plans/x.json --approuve

Le projet est le dossier courant. Les profils des agents sont lus dans
.github/agents/, à côté de ce script ou dans un dossier parent. Aucun agent
n'écrit sur le disque : le pilote contrôle chaque livraison, puis l'écrit lui-même.

Déroulement d'un plan :
  1. le pilote vérifie le plan, puis demande l'accord ;
  2. le développeur et le rédacteur de tests livrent en parallèle ; le pilote
     contrôle leurs livraisons, puis écrit les fichiers ;
  3. le testeur exécute pytest et cite, pour chaque critère, des tests passés ;
  4. si pytest échoue ou si un critère reste sans preuve acceptée, le testeur
     demande des corrections : au plus deux cycles de plus. Le bilan termine la trace.

Le pilote écrit la trace dans traces/<horodatage>-<plan>.md. Il note dans
traces/tests-crees.json les fichiers de tests qu'il crée : une relance du même
plan les reprend.

Code de sortie : 0 si le plan est VALIDÉ, 1 s'il est NON VALIDÉ, 2 s'il n'est pas
lancé. Une erreur qui arrête le pilote s'affiche « BLOQUÉ : ... », avec le code 1.

Le pilote vérifie que chaque preuve citée par le testeur est un test passé,
écrit pour ce plan. Il ne juge pas si ce test démontre le critère : relisez-le.
"""
import argparse
import asyncio
from datetime import datetime
import difflib
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile

DEV, REDACTEUR, TESTEUR = "developpeur", "redacteur-tests", "testeur"
# La liste du plan que livre chaque spécialiste ; le testeur ne livre aucun fichier.
CIBLES = {DEV: "code", REDACTEUR: "tests"}
# Le dossier de ce script : la recherche des profils part de là.
ICI = Path(__file__).resolve().parent
# Les fichiers de tests que le pilote a créés, avec le plan qui les a demandés.
REGISTRE = Path("traces") / "tests-crees.json"
# Comptes de la ligne de résumé de pytest, traduits pour la trace.
COMPTES_PYTEST = {"passed": "réussis", "failed": "en échec", "error": "en erreur",
                  "errors": "en erreur", "skipped": "ignorés", "xfailed": "xfail",
                  "xpassed": "xpass"}


def duree(debut, fin):
    """Formate le temps écoulé entre deux datetime debut et fin.

    Renvoie une chaîne en secondes ou en minutes et secondes."""
    secondes = (fin - debut).total_seconds()
    if secondes < 60:
        return f"{secondes:.1f} s"
    return f"{int(secondes // 60)} min {int(secondes % 60):02d} s"


def resume_pytest(texte):
    """Résume les comptes de la ligne de résumé finale de pytest.

    Renvoie une chaîne lisible, par exemple « réussis : 11 sur 12 (en échec : 1) »,
    ou « résumé pytest introuvable »."""
    lignes = [ligne for ligne in texte.splitlines() if ligne.startswith("=") and " in " in ligne]
    if not lignes:
        return "résumé pytest introuvable"
    comptes = {mot: int(n) for n, mot in re.findall(r"(\d+) (\w+)", lignes[-1])
               if mot in COMPTES_PYTEST}
    resume = f"réussis : {comptes.get('passed', 0)} sur {sum(comptes.values())}"
    autres = [f"{COMPTES_PYTEST[mot]} : {n}" for mot, n in comptes.items() if mot != "passed"]
    return resume + (f" ({', '.join(autres)})" if autres else "")


def fichier_de_preuve(identifiant):
    """Extrait de l'identifiant d'un test pytest le chemin de son fichier.

    Renvoie par exemple « tests/test_x.py » pour « tests/test_x.py::test_y »."""
    return identifiant.split("::", 1)[0]


def juger_preuve(ids, passes, tests_du_plan):
    """Contrôle les références citées pour un critère.

    ids contient les identifiants cités, passes ceux réellement réussis et
    tests_du_plan les chemins de tests autorisés. Renvoie None si les références
    sont acceptées, sinon un message de refus. Ne juge pas les assertions."""
    if not ids or not all(isinstance(i, str) for i in ids):
        return "preuve absente"
    for identifiant in ids:
        if identifiant not in passes:
            return f"preuve refusée : {identifiant} ne figure pas parmi les tests passés"
        if fichier_de_preuve(identifiant) not in tests_du_plan:
            return f"preuve refusée : {identifiant} n'est pas un test de ce plan"
    return None


def cellule(texte):
    """Met texte sur une seule ligne et échappe les barres d'un tableau Markdown.

    Renvoie la chaîne obtenue."""
    return " ".join(str(texte).split()).replace("|", "\\|")


class Trace:
    """Journal horodaté d'une exécution : dans le terminal, et dans un fichier Markdown.

    Chaque événement est écrit dès qu'il se produit : la trace reste lisible
    même si le pilote s'arrête en cours de route. Le bilan la termine.
    """

    def __init__(self, chemin=None):
        """Initialise la trace.

        chemin désigne le fichier Markdown ; avec None, la trace reste au terminal."""
        self.chemin = chemin
        self.depart = datetime.now()
        self.sessions = []
        self.tests = None
        self.preuves = {}

    def _ecrire(self, texte):
        """Ajoute texte au fichier de trace lorsqu'un chemin a été configuré."""
        if self.chemin:
            with open(self.chemin, "a", encoding="utf-8") as fichier:
                fichier.write(texte)

    def ouvrir(self, plan, chemin_plan, commande, approbation):
        """Commence la trace avec le plan, son chemin et le mode d'approbation.

        commande est la commande pytest. Écrit les critères et la vérification
        prévue, puis journalise le démarrage."""
        if self.chemin:
            self.chemin.parent.mkdir(parents=True, exist_ok=True)
        criteres = "".join(f"- **{cle}** : {attendu}\n" for cle, attendu in plan["criteres"].items())
        self._ecrire(
            f"# Trace du pilote : {chemin_plan.stem}\n\n"
            f"- Plan : `{chemin_plan}`, approuvé {approbation}\n"
            f"- Début : {self.depart:%Y-%m-%d %H:%M:%S}\n"
            f"- Objectif : {plan['objectif']}\n"
            f"- Fichiers de code : {', '.join(plan['code'])}\n"
            f"- Fichiers de tests : {', '.join(plan['tests'])}\n"
            f"- Contexte : {', '.join(plan['contexte']) or 'aucun'}\n"
            f"- Vérification : `{shlex.join(commande)}`\n\n"
            f"## Critères\n\n{criteres}\n## Chronologie\n\n")
        self.evenement("pilote", f"plan approuvé {approbation}"
                       + (f", trace dans {self.chemin}" if self.chemin else ""))

    def evenement(self, acteur, texte):
        """Affiche et journalise texte pour acteur, avec heure et durée écoulée.

        Renvoie le datetime de l'événement."""
        maintenant = datetime.now()
        ecoule = (maintenant - self.depart).total_seconds()
        texte = " ".join(str(texte).split())
        print(f"{maintenant:%H:%M:%S} +{ecoule:6.1f}s  {acteur:<15}  {texte}", flush=True)
        self._ecrire(f"- `{maintenant:%H:%M:%S}` `+{ecoule:.1f} s` **{acteur}** : {texte}\n")
        return maintenant

    def bloc(self, titre, contenu, langage=""):
        """Ajoute à la trace un bloc repliable nommé titre contenant contenu.

        contenu est une consigne, un diff, une sortie pytest ou un rapport ; langage
        indique le langage du bloc Markdown. Rien n'est affiché au terminal."""
        cloture = "`" * max([3] + [len(suite) + 1 for suite in re.findall(r"`+", contenu)])
        self._ecrire(f"\n<details><summary>{html.escape(titre)}</summary>\n\n"
                     f"{cloture}{langage}\n{contenu.rstrip()}\n{cloture}\n\n</details>\n\n")

    def commencer(self, role, mission):
        """Enregistre le début de la mission de role ; renvoie sa fiche de session."""
        session = {"role": role, "fin": None, "issue": "en cours", "fichiers": []}
        self.sessions.append(session)
        session["debut"] = self.evenement(role, f"commence : {mission}")
        return session

    def finir(self, session, issue):
        """Clôture la session avec son issue et journalise sa durée."""
        session["issue"] = issue
        temps = duree(session["debut"], datetime.now())
        session["fin"] = self.evenement(session["role"], f"termine en {temps} : {issue}")

    def _derniere(self, role):
        """Renvoie la dernière fiche de session de role, ou None s'il n'en a pas."""
        return next((s for s in reversed(self.sessions) if s["role"] == role), None)

    def preciser(self, role, issue):
        """Remplace l'issue de la dernière session de role, si elle existe.

        Le testeur y reçoit par exemple le bilan de pytest et des preuves."""
        session = self._derniere(role)
        if session:
            session["issue"] = issue

    def fichier_ecrit(self, role, nom, avant, apres):
        """Trace le diff et le résumé d'un fichier livré par role.

        nom est son chemin ; avant est son ancien contenu ou None pour une création ;
        apres est le nouveau contenu."""
        diff = difflib.unified_diff(
            [] if avant is None else avant.splitlines(keepends=True),
            apres.splitlines(keepends=True),
            "/dev/null" if avant is None else f"a/{nom}", f"b/{nom}")
        lignes = [ligne if ligne.endswith("\n") else ligne + "\n" for ligne in diff]
        corps = lignes[2:]
        ajouts = sum(ligne.startswith("+") for ligne in corps)
        retraits = sum(ligne.startswith("-") for ligne in corps)
        resume = f"{nom} ({'créé' if avant is None else 'modifié'}, +{ajouts} -{retraits})"
        session = self._derniere(role)
        if session:
            session["fichiers"].append(resume)
        self.evenement("pilote", f"écrit {resume}, livré par {role}")
        self.bloc(f"Diff de {nom}, livré par {role}", "".join(lignes), "diff")

    def terminer(self, verdict):
        """Affiche et écrit le bilan : sessions, tests, preuves et verdict.

        verdict est le texte final, par exemple « VALIDÉ » ou « BLOQUÉ : ... »."""
        fin = self.evenement("pilote", verdict)
        total = duree(self.depart, fin)
        print("\nBILAN", flush=True)
        markdown = ["", "## Bilan", "",
                    "| Agent | Début | Fin | Durée | Ce qu'il a fait | Fichiers écrits |",
                    "|---|---|---|---|---|---|"]
        for session in self.sessions:
            debut, arret = session["debut"], session["fin"] or fin
            temps = duree(debut, arret)
            print(f"  {session['role']:<15}  {debut:%H:%M:%S} → {arret:%H:%M:%S}  {temps:>10}  "
                  f"{session['issue']}")
            for fichier in session["fichiers"]:
                print(f"  {'':<15}  écrit {fichier}")
            markdown.append(f"| {session['role']} | {debut:%H:%M:%S} | {arret:%H:%M:%S} | {temps} "
                            f"| {cellule(session['issue'])} "
                            f"| {cellule(', '.join(session['fichiers']) or 'aucun')} |")
        if self.tests:
            print(f"  Tests : {self.tests}")
            markdown += ["", f"**Tests** : {self.tests}"]
        if self.preuves:
            markdown += ["", "| Critère | Tests cités par le testeur |", "|---|---|"]
            for critere, preuve in self.preuves.items():
                print(f"  {critere} : {preuve}")
                markdown.append(f"| {critere} | {cellule(preuve)} |")
            limite = ("Le pilote a vérifié que ces tests ont passé et viennent du plan ; il ne juge "
                      "pas s'ils démontrent le critère : relisez-les.")
            print(f"  {limite}")
            markdown += ["", limite]
        print(f"  Verdict : {verdict}, durée totale {total}")
        markdown += ["", f"**Verdict : {cellule(verdict)}**, durée totale {total}.", ""]
        self._ecrire("\n".join(markdown) + "\n")
        if self.chemin:
            print(f"Trace complète : {self.chemin}", flush=True)


def definition_agent(role):
    """Lit le profil Markdown de role dans .github/agents/.

    Cherche à côté de ce script, puis dans chaque dossier parent : la démo utilise
    les profils de la racine de la formation. Renvoie le texte du profil ; lève
    FileNotFoundError s'il est introuvable."""
    for dossier in (ICI, *ICI.parents):
        chemin = dossier / ".github" / "agents" / f"{role}.agent.md"
        if chemin.is_file():
            return chemin.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Profil introuvable : .github/agents/{role}.agent.md")


def fichier_projet(racine, nom):
    """Valide le chemin relatif nom sous racine et renvoie son objet Path.

    Lève ValueError pour un chemin absolu, ambigu, non canonique ou extérieur."""
    if not isinstance(nom, str) or not nom or Path(nom).is_absolute():
        raise ValueError(f"Chemin relatif attendu : {nom!r}")
    chemin = racine / nom
    if chemin.resolve() != chemin or chemin == racine or not chemin.is_relative_to(racine):
        raise ValueError(f"Chemin ambigu ou extérieur : {nom}")
    if nom != chemin.relative_to(racine).as_posix():
        raise ValueError(f"Utiliser un chemin relatif canonique : {nom}")
    return chemin


def charger_plan(racine, chemin_plan):
    """Charge et valide le plan JSON situé à chemin_plan pour le projet racine.

    Renvoie le dictionnaire du plan, avec une liste contexte par défaut. Lève une
    erreur si l'objectif, les critères, les chemins ou les tests existants sont
    invalides ; les fichiers de code et de tests sont des fichiers Python."""
    plan = json.loads(chemin_plan.read_text(encoding="utf-8"))
    if not isinstance(plan.get("objectif"), str) or not plan["objectif"].strip():
        raise ValueError("Objectif manquant.")
    criteres = plan.get("criteres")
    if not isinstance(criteres, dict) or not criteres or not all(
        k.strip() and isinstance(v, str) and v.strip() for k, v in criteres.items()
    ):
        raise ValueError("Chaque critère doit avoir un identifiant et un attendu.")
    vus = set()
    for groupe in ("code", "tests", "contexte"):
        entrees = plan.setdefault(groupe, []) if groupe == "contexte" else plan.get(groupe)
        if not isinstance(entrees, list) or (groupe != "contexte" and not entrees):
            raise ValueError(f"Liste de fichiers attendue pour {groupe}.")
        for nom in entrees:
            chemin = fichier_projet(racine, nom)
            if groupe == "contexte" and not chemin.is_file():
                raise ValueError(f"Contexte introuvable : {nom}")
            if groupe != "contexte" and chemin.suffix != ".py":
                raise ValueError(f"La cible doit être un fichier Python : {nom}")
            if nom in vus:
                raise ValueError(f"Chemin en double dans le plan : {nom}")
            vus.add(nom)
    verifier_tests_existants(racine, plan, identite_plan(racine, chemin_plan, plan))
    return plan


def identite_plan(racine, chemin_plan, plan):
    """Construit l'identité du plan à partir de son chemin et de son contenu.

    racine est le projet, chemin_plan le fichier et plan le dictionnaire chargé.
    Renvoie {"plan": chemin, "empreinte": hash}. Le chemin distingue deux plans de
    même nom rangés dans deux dossiers ; l'empreinte distingue deux versions d'un
    même plan, dont le contrat a changé."""
    chemin = chemin_plan.resolve()
    try:
        nom = chemin.relative_to(racine.resolve()).as_posix()
    except ValueError:
        nom = chemin.as_posix()
    contenu = json.dumps(plan, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return {"plan": nom, "empreinte": hashlib.sha256(contenu).hexdigest()[:16]}


def tests_crees(racine):
    """Lit le registre des tests créés sous racine.

    Renvoie un dictionnaire chemin → identité du plan, ou {} si le registre
    est absent, illisible ou invalide. Dans ce cas, aucun test n'est reconnu :
    le pilote refuse de réécrire un test existant plutôt que de le croire sien."""
    try:
        registre = json.loads((racine / REGISTRE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return registre if isinstance(registre, dict) else {}


def noter_tests_crees(racine, proprietaire, noms):
    """Enregistre les chemins noms comme tests créés par proprietaire sous racine.

    Le registre est écrit par remplacement atomique ; aucun résultat n'est renvoyé."""
    registre = tests_crees(racine)
    registre.update({nom: proprietaire for nom in noms})
    texte = json.dumps(registre, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    remplacer(racine / REGISTRE, texte.encode("utf-8"))


def verifier_tests_existants(racine, plan, proprietaire):
    """Vérifie que les tests existants du plan appartiennent à proprietaire.

    racine est le projet et proprietaire l'identité du plan. Un test absent du
    disque sera créé ; un test présent doit avoir été créé par ce plan, dans cette
    version, d'après le registre. Lève ValueError pour un test d'une version
    précédente du plan, d'un autre plan, ou que le registre ne connaît pas : test
    du projet, ou registre perdu."""
    crees = tests_crees(racine)
    for nom in plan["tests"]:
        if not fichier_projet(racine, nom).exists() or crees.get(nom) == proprietaire:
            continue
        origine = crees.get(nom)
        if isinstance(origine, dict) and origine.get("plan") == proprietaire["plan"]:
            raise ValueError(f"Test existant : {nom}. Il vient d'une version précédente de ce plan, "
                             "dont le contrat a changé : supprimez-le pour qu'il soit réécrit, ou "
                             "laissez-le dans le contexte et choisissez un nouveau fichier.")
        raise ValueError(f"Test existant : {nom}. Il ne vient pas d'un essai de ce plan, d'après "
                         f"{REGISTRE.as_posix()} : laissez-le dans le contexte et choisissez un "
                         "nouveau fichier.")


def instantane(racine, plan):
    """Lit les fichiers de code, tests et contexte du plan sous racine.

    Renvoie un dictionnaire chemin → octets, ou None si le fichier n'existe pas."""
    fichiers = {}
    for groupe in ("code", "tests", "contexte"):
        for nom in plan[groupe]:
            chemin = fichier_projet(racine, nom)
            fichiers[nom] = chemin.read_bytes() if chemin.exists() else None
    return fichiers


def en_texte(fichiers):
    """Convertit un instantané chemin → octets ou None en textes UTF-8 ou None.

    Renvoie un nouveau dictionnaire destiné aux messages envoyés aux agents."""
    return {nom: donnees.decode("utf-8-sig") if donnees is not None else None
            for nom, donnees in fichiers.items()}


def remplacer(chemin, donnees):
    """Écrit les octets donnees à chemin par remplacement atomique.

    Crée le dossier parent et conserve les permissions d'un fichier existant."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=chemin.parent, delete=False) as tmp:
        temporaire = Path(tmp.name)
    try:
        temporaire.write_bytes(donnees)
        if chemin.exists():
            temporaire.chmod(chemin.stat().st_mode)
        os.replace(temporaire, chemin)
    finally:
        temporaire.unlink(missing_ok=True)


def appliquer_livraisons(racine, plan, avant, livraisons, trace, proprietaire=None,
                         correction=False):
    """Contrôle puis écrit les livraisons des spécialistes.

    racine et plan définissent le projet et les cibles ; avant est l'instantané
    pris avant les appels ; livraisons associe chaque rôle à sa réponse JSON ;
    trace journalise les changements. proprietaire identifie le plan pour le
    registre des tests ; correction impose une modification lors d'une correction.
    Lève une erreur si une livraison ou l'état des fichiers est invalide."""
    changements, auteurs = {}, {}
    for role, livraison in livraisons.items():
        if livraison.get("statut") != "livre":
            raise ValueError(f"{role} bloqué : {livraison.get('raison', 'livraison absente')}")
        fichiers = livraison.get("fichiers")
        if (not isinstance(fichiers, dict) or not fichiers
                or not fichiers.keys() <= set(plan[CIBLES[role]])):
            raise ValueError(f"Livraison absente ou hors du plan pour {role}.")
        modifies = {}
        for nom, code in fichiers.items():
            if not isinstance(code, str) or not code.strip():
                raise ValueError(f"Contenu manquant : {nom}")
            compile(code, nom, "exec")
            if avant[nom] is None or code != avant[nom].decode("utf-8-sig"):
                modifies[nom] = code.encode("utf-8")
        if not modifies:
            # Au premier cycle d'une relance, des fichiers déjà justes peuvent revenir intacts ;
            # une correction demandée doit, elle, changer quelque chose.
            if correction:
                raise ValueError(f"{role} n'a livré aucune modification.")
            trace.evenement("pilote", f"{role} livre ses fichiers à l'identique : rien à écrire")
        changements.update(modifies)
        auteurs.update(dict.fromkeys(modifies, role))
    trace.evenement("pilote", "livraisons contrôlées : chemins autorisés, contenus non vides, "
                              "syntaxe Python valide")
    if instantane(racine, plan) != avant:
        raise ValueError("Un fichier du plan a changé pendant les appels. Réexaminer le plan.")
    trace.evenement("pilote", "fichiers du plan inchangés depuis l'envoi aux agents : écriture")
    # Le registre est écrit avant les tests qu'il décrit : un test sur le disque est toujours
    # inscrit. Si l'écriture du registre échoue, rien n'est écrit.
    crees = [nom for nom in changements if avant[nom] is None and nom in plan["tests"]]
    if crees and proprietaire:
        noter_tests_crees(racine, proprietaire, crees)
    ecrits = []
    try:
        for nom, donnees in changements.items():
            remplacer(fichier_projet(racine, nom), donnees)
            ecrits.append(nom)
            # Une correction de même taille peut garder le même horodatage à la seconde.
            chemin = fichier_projet(racine, nom)
            for cache in (chemin.parent / "__pycache__").glob(chemin.stem + ".*.pyc"):
                cache.unlink(missing_ok=True)
    except OSError:
        for nom in reversed(ecrits):
            chemin = fichier_projet(racine, nom)
            if avant[nom] is None:
                chemin.unlink()
            else:
                remplacer(chemin, avant[nom])
        raise
    for nom, donnees in changements.items():
        anterieur = None if avant[nom] is None else avant[nom].decode("utf-8-sig")
        trace.fichier_ecrit(auteurs[nom], nom, anterieur, donnees.decode("utf-8"))


async def demander(client, racine, role, message, outils=()):
    """Ouvre une session Copilot pour role et lui envoie message.

    client est le SDK, racine le dossier de travail et outils les outils fournis.
    Le spécialiste ne reçoit que son profil et message : la découverte de
    configuration est désactivée, il ne lit ni AGENTS.md ni la configuration du
    dépôt, sauf ce que le plan met dans le contexte. Toute demande de permission
    est refusée, écriture comprise. Renvoie la réponse JSON sous forme de
    dictionnaire ; lève ValueError si elle est vide ou n'est pas un objet JSON."""
    from copilot.rpc import PermissionDecisionReject

    corps = definition_agent(role).split("---", 2)[2].strip()
    noms = [outil.name for outil in outils]
    async with await client.create_session(
        working_directory=str(racine),
        enable_config_discovery=False,
        agents={"definitions": [{"name": role, "prompt": corps, "tools": noms}], "selected": role},
        tools={"definitions": list(outils), "available_tools": noms},
        permissions={"on_request": lambda request, invocation: PermissionDecisionReject()},
    ) as session:
        resultat = await session.send_and_wait(message, timeout=900)
        contenu = getattr(getattr(resultat, "data", None), "content", None)
        if not isinstance(contenu, str) or not contenu.strip():
            raise ValueError(f"{role} a terminé sans réponse.")
        reponse = contenu.strip()
        if reponse.startswith("```") and reponse.endswith("```"):
            reponse = reponse.split("\n", 1)[1][:-3].strip()
        valeur = json.loads(reponse)
        if not isinstance(valeur, dict):
            raise ValueError(f"Réponse JSON invalide de {role}.")
    return valeur


async def confier(client, racine, trace, role, mission, consigne, contexte, outils=()):
    """Confie une mission à role et trace le déroulement de sa session.

    client, racine et outils configurent l'appel ; consigne et contexte forment
    le message ; trace reçoit les événements. Renvoie la réponse de l'agent et
    propage les erreurs après les avoir journalisées."""
    session = trace.commencer(role, mission)
    trace.bloc(f"Consigne envoyée à {role}, suivie du plan et des sources", consigne)
    try:
        reponse = await demander(client, racine, role, consigne + contexte, outils)
    except asyncio.CancelledError:
        trace.finir(session, "annulé : une autre session du lot a échoué")
        raise
    except Exception as erreur:
        trace.finir(session, f"en erreur : {expliquer(erreur)}")
        raise
    if role == TESTEUR:
        issue = "rapport rendu"
    elif reponse.get("statut") == "livre" and isinstance(reponse.get("fichiers"), dict):
        issue = "livre " + ", ".join(map(str, reponse["fichiers"]))
    else:
        issue = f"bloqué : {reponse.get('raison', 'livraison absente')}"
    trace.finir(session, issue)
    return reponse


async def lancer_pytest(racine, commande, trace):
    """Exécute la commande pytest dans racine pour le testeur, et la trace.

    Renvoie (code de sortie, sortie complète, identifiants des tests passés). Les
    identifiants viennent des lignes « PASSED ... », que pytest n'écrit qu'avec
    -rA. Arrête le processus en cas d'annulation ou après dix minutes."""
    debut = trace.evenement("pilote", "exécute pytest pour le testeur : " + shlex.join(commande))
    processus = await asyncio.create_subprocess_exec(
        *commande, cwd=racine, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    try:
        sortie, _ = await asyncio.wait_for(processus.communicate(), timeout=600)
    except (TimeoutError, asyncio.CancelledError):
        if processus.returncode is None:
            processus.kill()
        await processus.wait()
        raise
    texte = sortie.decode("utf-8", errors="replace")
    print(texte, flush=True)
    passes = set(re.findall(r"^PASSED (.+?)$", texte, flags=re.M))
    trace.evenement("pilote", f"pytest terminé en {duree(debut, datetime.now())} : code de sortie "
                              f"{processus.returncode}, {resume_pytest(texte)}")
    trace.bloc("Sortie complète de pytest", texte)
    return processus.returncode, texte, passes


async def evaluer(client, racine, plan, fichiers, commande, trace):
    """Confie au testeur l'exécution de pytest et contrôle son rapport.

    client est le SDK, racine le projet, plan le contrat, fichiers son instantané,
    commande la commande pytest et trace le journal. Renvoie (valide, corrections).
    Les tests cités doivent avoir réussi et venir du plan ; leur pertinence reste à
    relire humainement."""
    from copilot.tools import Tool, ToolResult

    execution = None
    verrou = asyncio.Lock()

    async def executer(_invocation):
        """Exécute pytest une seule fois et renvoie son rapport au testeur."""
        nonlocal execution
        async with verrou:
            if execution is None:
                execution = await lancer_pytest(racine, commande, trace)
        code, sortie, passes = execution
        return ToolResult(text_result_for_llm=json.dumps({
            "code_sortie": code, "sortie": sortie[-24000:], "passes": sorted(passes)
        }, ensure_ascii=False))

    outil = Tool("executer_pytest", "Exécute la suite complète, dans le projet courant.", executer,
                 parameters={"type": "object", "properties": {}, "additionalProperties": False},
                 skip_permission=True, defer="never")
    message = ('Appelle executer_pytest. Lis les assertions, puis retourne uniquement un objet JSON '
               '{"preuves":{"CA1":["identifiant pytest passé"]},"diagnostic":"...","corrections":{}}. '
               f'Dans preuves, ne cite que des tests passés des fichiers {plan["tests"]}, dont '
               'les assertions démontrent le critère ; pour un critère à plusieurs variantes, cite '
               'un test par variante. '
               'En cas de défaut corrigeable, corrections associe le nom exact du spécialiste '
               'developpeur ou redacteur-tests à une instruction précise. Pour un incident '
               'environnemental ou une ambiguïté, explique le blocage et laisse corrections vide.\n')
    rapport = await confier(client, racine, trace, TESTEUR,
                            "exécute pytest et relie chaque critère à des tests passés", message,
                            json.dumps([plan, en_texte(fichiers)], ensure_ascii=False), [outil])
    if execution is None:
        trace.preciser(TESTEUR, "a répondu sans exécuter pytest")
        raise ValueError("Le testeur a répondu sans exécuter pytest.")
    code, sortie, passes = execution
    trace.tests = f"{resume_pytest(sortie)}, code de sortie {code}"
    preuves = rapport.get("preuves", {})
    valide = code == 0
    trace.preuves = {}
    couverts, cites = 0, set()
    for critere in plan["criteres"]:
        ids = preuves.get(critere) if isinstance(preuves, dict) else None
        ids = ids if isinstance(ids, list) else []
        refus = juger_preuve(ids, passes, set(plan["tests"]))
        valide = valide and refus is None
        if refus is None:
            couverts += 1
            cites.update(fichier_de_preuve(i) for i in ids)
        trace.preuves[critere] = refus or ", ".join(ids)
        trace.evenement("pilote", f"{critere} : {refus}" if refus
                        else f"{critere} : tests cités, passés, du plan : {', '.join(ids)}")
    # Un fichier de tests du plan existe pour être cité.
    for nom in plan["tests"]:
        if nom not in cites:
            valide = False
            trace.evenement("pilote", f"{nom} n'est cité pour aucun critère")
    diagnostic = str(rapport.get("diagnostic", "")).strip()
    if diagnostic:
        trace.evenement(TESTEUR, f"diagnostic : {diagnostic}")
    corrections = rapport.get("corrections", {})
    if isinstance(corrections, dict):
        for destinataire, instruction in corrections.items():
            trace.evenement(TESTEUR, f"correction demandée à {destinataire} : {instruction}")
    trace.preciser(TESTEUR, f"pytest {trace.tests} ; critères avec tests cités, passés, du plan : "
                            f"{couverts} sur {len(trace.preuves)}")
    trace.bloc("Rapport brut du testeur", json.dumps(rapport, ensure_ascii=False, indent=2), "json")
    return valide, corrections


async def cycles(client, racine, plan, commande, trace, proprietaire=None):
    """Exécute jusqu'à trois cycles de livraison et de vérification du plan.

    client, racine et trace servent aux appels et au journal ; commande est la
    commande pytest ; proprietaire identifie le plan pour les tests créés. Renvoie
    « VALIDÉ » ou « NON VALIDÉ »."""
    missions = {DEV: "Implémente le plan.", REDACTEUR: "Écris les tests du plan."}
    for tentative in range(3):
        avant = instantane(racine, plan)
        contexte = json.dumps({"plan": plan, "sources": en_texte(avant)}, ensure_ascii=False)
        livraisons = {}

        async def livrer(role, mission):
            """Confie mission à role et range sa réponse dans livraisons."""
            consigne = (
                f"{mission}\nTes fichiers autorisés : {plan[CIBLES[role]]}. "
                'Réponds exclusivement en JSON : {"statut":"livre","fichiers":{"chemin":"contenu complet"}} '
                'ou {"statut":"bloque","raison":"..."}. Conserve le contenu existant pertinent.\n'
            )
            livraisons[role] = await confier(client, racine, trace, role, mission, consigne, contexte)

        if tentative == 0:
            trace.evenement("pilote", f"cycle 1 : lance {' et '.join(missions)} en parallèle")
        else:
            trace.evenement("pilote", f"cycle {tentative + 1}, correction : relance "
                                      f"{' et '.join(missions)}")
        # La sortie de TaskGroup attend toutes les livraisons. Une exception annule le lot.
        async with asyncio.TaskGroup() as groupe:
            for role, mission in missions.items():
                groupe.create_task(livrer(role, mission))
        appliquer_livraisons(racine, plan, avant, livraisons, trace, proprietaire,
                             correction=tentative > 0)
        trace.evenement("pilote", f"vérification {tentative + 1} : passe la main au testeur")
        valide, missions = await evaluer(client, racine, plan, instantane(racine, plan), commande,
                                         trace)
        if valide:
            return "VALIDÉ"
        if not isinstance(missions, dict) or not missions or not missions.keys() <= CIBLES.keys():
            break
        if not all(isinstance(s, str) and s.strip() for s in missions.values()):
            break
    return "NON VALIDÉ"


async def pipeline(client, racine, plan, commande, trace, proprietaire=None):
    """Orchestre les cycles du plan et termine la trace avec un bilan.

    client est le SDK, racine le projet, commande la commande pytest et trace le
    journal. proprietaire est l'identité du plan : les tests créés sont inscrits à
    son nom, pour qu'une relance du même plan les reprenne. Renvoie 0 si validé,
    1 sinon ; trace puis propage toute exception qui bloque le pipeline."""
    try:
        verdict = await cycles(client, racine, plan, commande, trace, proprietaire)
    except BaseException as erreur:
        trace.terminer(f"BLOQUÉ : {expliquer(erreur)}")
        raise
    trace.terminer(verdict)
    return 0 if verdict == "VALIDÉ" else 1


async def main():
    """Lit les options de commande et lance un plan approuvé.

    Le projet est le dossier courant. Demande l'accord sauf avec --approuve, ouvre
    le client Copilot et renvoie le code de sortie du pipeline, ou 2 si le plan
    n'est pas lancé."""
    analyseur = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    analyseur.add_argument("--plan", type=Path, required=True, help="Plan JSON du projet")
    analyseur.add_argument("--approuve", action="store_true",
                           help="Le demandeur a déjà approuvé ce plan")
    analyseur.add_argument("--pytest-python", help="Interpréteur Python du projet contenant pytest")
    args = analyseur.parse_args()
    racine = Path.cwd().resolve()
    plan = charger_plan(racine, args.plan)
    if not args.approuve:
        print(json.dumps(plan, ensure_ascii=False, indent=2), flush=True)
        if input("Démarrer ce plan ? [oui/non] ").strip().casefold() != "oui":
            print("Plan non lancé.", flush=True)
            return 2
    from copilot import CopilotClient
    prefixe = [args.pytest_python] if args.pytest_python else ["uv", "run", "--locked", "python"]
    # -rA termine la sortie par une ligne « PASSED ... » par test réussi : lancer_pytest
    # les lit. --color=no garde ces lignes lisibles.
    commande = prefixe + ["-m", "pytest", "-v", "--tb=short", "-rA", "--color=no"]
    async with CopilotClient(mode="coding-agent") as client:
        if not (await client.get_auth_status()).is_authenticated:
            raise RuntimeError("Authentifie Copilot CLI avec copilot login, puis relance ce plan.")
        horodatage = datetime.now().strftime("%Y%m%d-%H%M%S")
        trace = Trace(Path("traces") / f"{horodatage}-{args.plan.stem}.md")
        trace.ouvrir(plan, args.plan, commande,
                     "dans le chat (--approuve)" if args.approuve else "au terminal")
        for nom in plan["tests"]:
            if (racine / nom).exists():
                trace.evenement("pilote", f"reprend {nom}, créé par un essai précédent de ce plan")
        return await pipeline(client, racine, plan, commande, trace,
                              identite_plan(racine, args.plan, plan))


def expliquer(erreur):
    """Transforme une erreur, éventuellement un groupe d'erreurs, en texte lisible."""
    if isinstance(erreur, BaseExceptionGroup):
        return " / ".join(expliquer(enfant) for enfant in erreur.exceptions)
    return str(erreur) or type(erreur).__name__


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except (KeyboardInterrupt, EOFError):
        sys.exit("Interrompu.")
    except Exception as erreur:
        sys.exit(f"BLOQUÉ : {expliquer(erreur)}")
