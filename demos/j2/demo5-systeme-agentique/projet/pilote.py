# /// script
# requires-python = ">=3.11"
# dependencies = ["microsoft-copilot-sdk==2.0.1"]
# ///
"""Pilote les trois spécialistes après validation du plan par l'orchestrateur VS Code."""
import argparse
import asyncio
from datetime import datetime
import difflib
import html
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile

DEV, REDACTEUR, TESTEUR = "developpeur", "redacteur-tests", "testeur"
CIBLES = {DEV: "code", REDACTEUR: "tests"}
ICI = Path(__file__).resolve().parent
# Comptes de la ligne de résumé de pytest, traduits pour la trace.
COMPTES_PYTEST = {"passed": "réussis", "failed": "en échec", "error": "en erreur",
                  "errors": "en erreur", "skipped": "ignorés", "xfailed": "xfail",
                  "xpassed": "xpass"}


def duree(debut, fin):
    secondes = (fin - debut).total_seconds()
    if secondes < 60:
        return f"{secondes:.1f} s"
    return f"{int(secondes // 60)} min {int(secondes % 60):02d} s"


def resume_pytest(texte):
    """« réussis : 11 sur 11 », d'après la ligne de résumé finale de pytest."""
    lignes = [ligne for ligne in texte.splitlines() if ligne.startswith("=") and " in " in ligne]
    if not lignes:
        return "résumé pytest introuvable"
    comptes = {mot: int(n) for n, mot in re.findall(r"(\d+) (\w+)", lignes[-1])
               if mot in COMPTES_PYTEST}
    resume = f"réussis : {comptes.get('passed', 0)} sur {sum(comptes.values())}"
    autres = [f"{COMPTES_PYTEST[mot]} : {n}" for mot, n in comptes.items() if mot != "passed"]
    return resume + (f" ({', '.join(autres)})" if autres else "")


def cellule(texte):
    """Texte sur une ligne, sans casser un tableau Markdown."""
    return " ".join(str(texte).split()).replace("|", "\\|")


class Trace:
    """Journal horodaté d'une exécution : dans le terminal, et dans un fichier Markdown.

    Chaque événement est écrit dès qu'il se produit : la trace reste lisible
    même si le pilote s'arrête en cours de route. Le bilan la termine.
    """

    def __init__(self, chemin=None):
        self.chemin = chemin
        self.depart = datetime.now()
        self.sessions = []
        self.tests = None
        self.preuves = {}

    def _ecrire(self, texte):
        if self.chemin:
            with open(self.chemin, "a", encoding="utf-8") as fichier:
                fichier.write(texte)

    def ouvrir(self, plan, chemin_plan, commande, approbation):
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
        maintenant = datetime.now()
        ecoule = (maintenant - self.depart).total_seconds()
        texte = " ".join(str(texte).split())
        print(f"{maintenant:%H:%M:%S} +{ecoule:6.1f}s  {acteur:<15}  {texte}", flush=True)
        self._ecrire(f"- `{maintenant:%H:%M:%S}` `+{ecoule:.1f} s` **{acteur}** : {texte}\n")
        return maintenant

    def bloc(self, titre, contenu, langage=""):
        """Détail repliable, dans le fichier seulement : consigne, diff, sortie pytest, rapport."""
        cloture = "`" * max([3] + [len(suite) + 1 for suite in re.findall(r"`+", contenu)])
        self._ecrire(f"\n<details><summary>{html.escape(titre)}</summary>\n\n"
                     f"{cloture}{langage}\n{contenu.rstrip()}\n{cloture}\n\n</details>\n\n")

    def commencer(self, role, mission):
        session = {"role": role, "fin": None, "issue": "en cours", "fichiers": []}
        self.sessions.append(session)
        session["debut"] = self.evenement(role, f"commence : {mission}")
        return session

    def finir(self, session, issue):
        session["issue"] = issue
        temps = duree(session["debut"], datetime.now())
        session["fin"] = self.evenement(session["role"], f"termine en {temps} : {issue}")

    def _derniere(self, role):
        return next((s for s in reversed(self.sessions) if s["role"] == role), None)

    def preciser(self, role, issue):
        """Complète l'issue de la dernière session d'un rôle, par exemple avec pytest."""
        session = self._derniere(role)
        if session:
            session["issue"] = issue

    def fichier_ecrit(self, role, nom, avant, apres):
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
            markdown += ["", "| Critère | Preuve vérifiée dans la sortie pytest |", "|---|---|"]
            for critere, preuve in self.preuves.items():
                print(f"  {critere} : {preuve}")
                markdown.append(f"| {critere} | {cellule(preuve)} |")
        print(f"  Verdict : {verdict}, durée totale {total}")
        markdown += ["", f"**Verdict : {cellule(verdict)}**, durée totale {total}.", ""]
        self._ecrire("\n".join(markdown) + "\n")
        if self.chemin:
            print(f"Trace complète : {self.chemin}", flush=True)


def definition_agent(role):
    """Profil de l'agent : .github/agents/ à côté du script ou dans un dossier parent."""
    for dossier in (ICI, *ICI.parents):
        chemin = dossier / ".github" / "agents" / f"{role}.agent.md"
        if chemin.is_file():
            return chemin.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Profil introuvable : .github/agents/{role}.agent.md")


def fichier_projet(racine, nom):
    if not isinstance(nom, str) or not nom or Path(nom).is_absolute():
        raise ValueError(f"Chemin relatif attendu : {nom!r}")
    chemin = racine / nom
    if chemin.resolve() != chemin or chemin == racine or not chemin.is_relative_to(racine):
        raise ValueError(f"Chemin ambigu ou extérieur : {nom}")
    if nom != chemin.relative_to(racine).as_posix():
        raise ValueError(f"Utiliser un chemin relatif canonique : {nom}")
    return chemin


def charger_plan(racine, chemin_plan):
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
    return plan


def instantane(racine, plan):
    fichiers = {}
    for groupe in ("code", "tests", "contexte"):
        for nom in plan[groupe]:
            chemin = fichier_projet(racine, nom)
            fichiers[nom] = chemin.read_bytes() if chemin.exists() else None
    return fichiers


def en_texte(fichiers):
    return {nom: donnees.decode("utf-8-sig") if donnees is not None else None
            for nom, donnees in fichiers.items()}


def remplacer(chemin, donnees):
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


def appliquer_livraisons(racine, plan, avant, livraisons, trace):
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
            raise ValueError(f"{role} n'a livré aucune modification.")
        changements.update(modifies)
        auteurs.update(dict.fromkeys(modifies, role))
    trace.evenement("pilote", "livraisons contrôlées : chemins autorisés, contenus non vides, "
                              "syntaxe Python valide")
    if instantane(racine, plan) != avant:
        raise ValueError("Un fichier du plan a changé pendant les appels. Réexaminer le plan.")
    trace.evenement("pilote", "fichiers du plan inchangés depuis l'envoi aux agents : écriture")
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
    """Une session d'agent, tracée : début, consigne, fin, durée et issue."""
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
    from copilot.tools import Tool, ToolResult

    execution = None
    verrou = asyncio.Lock()

    async def executer(_invocation):
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
               'Dans preuves, ne cite que les tests réellement passés qui démontrent le critère. '
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
    for critere in plan["criteres"]:
        ids = preuves.get(critere) if isinstance(preuves, dict) else None
        couvert = (isinstance(ids, list) and bool(ids)
                   and all(isinstance(i, str) and i in passes for i in ids))
        valide = valide and couvert
        trace.preuves[critere] = ", ".join(ids) if couvert else "preuve absente"
        trace.evenement("pilote", f"{critere} : prouvé par {', '.join(ids)}" if couvert
                        else f"{critere} : preuve absente")
    diagnostic = str(rapport.get("diagnostic", "")).strip()
    if diagnostic:
        trace.evenement(TESTEUR, f"diagnostic : {diagnostic}")
    corrections = rapport.get("corrections", {})
    if isinstance(corrections, dict):
        for destinataire, instruction in corrections.items():
            trace.evenement(TESTEUR, f"correction demandée à {destinataire} : {instruction}")
    prouves = sum(preuve != "preuve absente" for preuve in trace.preuves.values())
    trace.preciser(TESTEUR, f"pytest {trace.tests} ; critères prouvés : {prouves} sur "
                            f"{len(trace.preuves)}")
    trace.bloc("Rapport brut du testeur", json.dumps(rapport, ensure_ascii=False, indent=2), "json")
    return valide, corrections


async def cycles(client, racine, plan, commande, trace):
    missions = {DEV: "Implémente le plan.", REDACTEUR: "Écris les tests du plan."}
    for tentative in range(3):
        avant = instantane(racine, plan)
        contexte = json.dumps({"plan": plan, "sources": en_texte(avant)}, ensure_ascii=False)
        livraisons = {}

        async def livrer(role, mission):
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
        appliquer_livraisons(racine, plan, avant, livraisons, trace)
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


async def pipeline(client, racine, plan, commande, trace):
    """Enchaîne livraisons et vérifications ; la trace se termine toujours par un bilan."""
    try:
        verdict = await cycles(client, racine, plan, commande, trace)
    except BaseException as erreur:
        trace.terminer(f"BLOQUÉ : {expliquer(erreur)}")
        raise
    trace.terminer(verdict)
    return 0 if verdict == "VALIDÉ" else 1


async def main():
    analyseur = argparse.ArgumentParser(description=__doc__)
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
    commande = prefixe + ["-m", "pytest", "-v", "--tb=short", "-rA", "--color=no"]
    async with CopilotClient(mode="coding-agent") as client:
        if not (await client.get_auth_status()).is_authenticated:
            raise RuntimeError("Authentifie Copilot CLI avec copilot login, puis relance ce plan.")
        horodatage = datetime.now().strftime("%Y%m%d-%H%M%S")
        trace = Trace(Path("traces") / f"{horodatage}-{args.plan.stem}.md")
        trace.ouvrir(plan, args.plan, commande,
                     "dans le chat (--approuve)" if args.approuve else "au terminal")
        return await pipeline(client, racine, plan, commande, trace)


def expliquer(erreur):
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
