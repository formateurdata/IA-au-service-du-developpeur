# /// script
# requires-python = ">=3.11"
# dependencies = ["microsoft-copilot-sdk==2.0.1", "pytest>=8"]
# ///
"""Tests du pilote, sans compte Copilot : doubles de sessions, vrai pytest, faux npm.

    uv run --script verification/test_pilote.py
"""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pilote  # noqa: E402

PROFILS_DU_LAB = pilote.PROFILS
FAUX_NPM = "npm-factice"
TEST_API = "api::tests/test_doubler.py::test_doubler"
TEST_WEB = "web::src/doubler.test.ts > doubler > double la valeur"
TEST_ANCIEN = "api::tests/test_ancien.py::test_ancien"
PROFIL = """---
name: {role}
description: Profil de test.
tools: {outils}
user-invocable: false
---

Consignes de test pour {role}.
"""


def ecrire(chemin, texte):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(texte, encoding="utf-8")


class Dossier(unittest.TestCase):
    """Un portail minimal dans un dossier temporaire : api/ et web/."""

    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.racine = Path(dossier.name).resolve() / "depart"
        ecrire(self.racine / "api" / "pytest.ini", "[pytest]\npythonpath = .\n")
        ecrire(self.racine / "api" / "app" / "__init__.py", "")
        ecrire(self.racine / "web" / "src" / "types.ts", "export type Valeur = number;\n")
        (self.racine / "web" / "node_modules").mkdir(parents=True)
        self.plan = {
            "objectif": "Doubler une valeur, côté API et côté interface",
            "criteres": {"CA1": "doubler(3) vaut 6 côté API",
                         "CA2": "doubler(3) vaut 6 côté interface"},
            "code": ["api/app/service.py", "web/src/doubler.ts"],
            "tests": ["api/tests/test_doubler.py", "web/src/doubler.test.ts"],
            "contexte": ["web/src/types.ts"],
        }

    def charger(self, plan=None):
        chemin = self.racine / "plan.json"
        ecrire(chemin, json.dumps(plan or self.plan, ensure_ascii=False))
        return pilote.charger_plan(self.racine, chemin)

    def identite(self, chemin="plan.json", plan=None):
        return pilote.identite_plan(self.racine, self.racine / chemin, plan or self.plan)


class TestsPipeline(Dossier, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        super().setUp()
        self.ordre = []
        self.cas = "ok"
        self.appels = 0
        self.trace = pilote.Trace(self.racine.parent / "trace.md")
        self.trace.ouvrir(self.plan, Path("plan.json"), "pour le test")

    async def agent(self, client, racine, role, message, outils=()):
        if role == pilote.DEV:
            await asyncio.sleep(0.025)
            if self.cas == "erreur":
                raise RuntimeError("session interrompue")
            self.ordre.append("code livré")
            if self.cas == "absente":
                return {"statut": "bloque", "raison": "contrat incomplet"}
            fichiers = {"api/app/service.py": "def doubler(x):\n    return 2 * x\n",
                        "web/src/doubler.ts": "export const doubler = (x: number) => 2 * x;\n"}
            if self.cas == "hors_plan":
                fichiers["api/tests/test_doubler.py"] = "def test_rien():\n    pass\n"
            return {"statut": "livre", "fichiers": fichiers}
        if role == pilote.REDACTEUR:
            self.ordre.append("tests livrés")
            self.appels += 1
            attendu = 7 if self.cas == "correction" and self.appels == 1 else 6
            return {"statut": "livre", "fichiers": {
                "api/tests/test_doubler.py": ("from app.service import doubler\n\n\n"
                                              "def test_doubler():\n"
                                              f"    assert doubler(3) == {attendu}\n"),
                "web/src/doubler.test.ts": "test('double la valeur', () => {});\n",
            }}
        self.ordre.append("testeur appelé")
        for nom in self.plan["code"] + self.plan["tests"]:
            self.assertTrue((racine / nom).is_file(), nom)
        self.noms_outils = [outil.name for outil in outils]
        executions = {}
        for outil in outils:
            if self.cas == "api_seule" and outil.name.endswith("_web"):
                continue
            resultat = await outil.handler(None)
            execution = json.loads(resultat.text_result_for_llm)
            executions[execution["suite"]] = execution
        if self.cas == "correction" and executions["api"]["code_sortie"] == 1:
            return {"preuves": {}, "corrections": {pilote.REDACTEUR: "CA1 impose 6."}}
        if self.cas == "correction_vide":
            return {"preuves": {}, "corrections": {pilote.REDACTEUR: "Renomme le test."}}
        preuve_web = {"inventee": "web::src/doubler.test.ts > test invente",
                      "hors_plan_preuve": TEST_ANCIEN, "api_partout": TEST_API}.get(self.cas, TEST_WEB)
        return {"preuves": {"CA1": [TEST_API], "CA2": [preuve_web]}, "corrections": {}}

    async def faux_executer(self, commande, dossier):
        """Remplace npm ; les autres commandes, dont pytest, s'exécutent vraiment."""
        if commande[0] != FAUX_NPM:
            return await self.executer_reel(commande, dossier)
        if commande[1:] == pilote.TYPECHECK:
            if self.cas == "typecheck":
                return 2, "src/doubler.ts(1,14): error TS2322: Type 'string' is not assignable.\n"
            return 0, "> tsc --noEmit\n"
        rapport = Path(commande[-1].split("=", 1)[1])
        ecrire(rapport, json.dumps({
            "numTotalTests": 1, "numPassedTests": 1, "numFailedTests": 0,
            "testResults": [{"name": str(dossier / "src" / "doubler.test.ts"),
                             "assertionResults": [{"status": "passed", "ancestorTitles": ["doubler"],
                                                   "title": "double la valeur"}]}]}))
        return 0, " ✓ src/doubler.test.ts > doubler > double la valeur\n"

    async def jouer(self):
        self.executer_reel = pilote.executer
        pytest = [sys.executable, "-m", "pytest", "-v", "--tb=short", "-rA", "--color=no",
                  "-p", "no:cacheprovider"]
        with patch.object(pilote, "demander", self.agent), \
                patch.object(pilote, "executer", self.faux_executer), \
                patch.object(pilote, "programme", lambda nom: FAUX_NPM), \
                patch.object(pilote, "PYTEST", pytest):
            return await pilote.pipeline(None, self.racine, self.plan, self.trace, self.identite())

    def lire_trace(self):
        return self.trace.chemin.read_text(encoding="utf-8")

    async def test_livraisons_puis_les_deux_suites(self):
        self.assertEqual(await self.jouer(), 0)
        self.assertEqual(self.ordre, ["tests livrés", "code livré", "testeur appelé"])
        self.assertEqual(self.noms_outils, ["executer_tests_api", "executer_tests_web"])

    async def test_un_plan_api_ne_donne_que_la_suite_api(self):
        self.plan["code"], self.plan["tests"] = ["api/app/service.py"], ["api/tests/test_doubler.py"]
        self.plan["criteres"] = {"CA1": self.plan["criteres"]["CA1"]}
        self.cas = "api_seule"
        origine = self.agent

        async def agent(client, racine, role, message, outils=()):
            reponse = await origine(client, racine, role, message, outils)
            if role == pilote.TESTEUR:
                return {"preuves": {"CA1": [TEST_API]}, "corrections": {}}
            return {**reponse, "fichiers": {nom: contenu for nom, contenu in reponse["fichiers"].items()
                                            if nom.startswith("api/")}}

        with patch.object(self, "agent", agent):
            self.assertEqual(await self.jouer(), 0)
        self.assertEqual(self.noms_outils, ["executer_tests_api"])

    async def test_le_testeur_doit_lancer_chaque_suite(self):
        self.cas = "api_seule"
        with self.assertRaisesRegex(ValueError, "sans exécuter la suite web"):
            await self.jouer()

    async def test_typecheck_en_echec(self):
        self.cas = "typecheck"
        self.assertEqual(await self.jouer(), 1)
        trace = self.lire_trace()
        self.assertIn("typecheck en échec (1 erreur), code de sortie 2", trace)
        self.assertIn("**Verdict : NON VALIDÉ**", trace)

    async def test_preuve_web_non_observee(self):
        self.cas = "inventee"
        self.assertEqual(await self.jouer(), 1)
        trace = self.lire_trace()
        self.assertIn("**pilote** : CA2 : preuve refusée : web::src/doubler.test.ts > test invente "
                      "ne figure pas parmi les tests passés", trace)
        self.assertIn("**Verdict : NON VALIDÉ**", trace)

    async def test_une_preuve_vient_d_un_test_du_plan(self):
        """Un test passé, mais écrit pour un autre ticket, ne prouve pas un critère de ce plan."""
        ecrire(self.racine / "api/tests/test_ancien.py", "def test_ancien():\n    pass\n")
        self.cas = "hors_plan_preuve"
        self.assertEqual(await self.jouer(), 1)
        self.assertIn(f"**pilote** : CA2 : preuve refusée : {TEST_ANCIEN} n'est pas un test de ce "
                      "plan", self.lire_trace())

    async def test_chaque_fichier_de_tests_prouve_un_critere(self):
        """Le ticket touche api/ et web/ : des preuves venues d'api/ seulement ne suffisent pas."""
        self.cas = "api_partout"
        self.assertEqual(await self.jouer(), 1)
        trace = self.lire_trace()
        self.assertIn(f"**pilote** : CA2 : tests cités, passés, du plan : {TEST_API}", trace)
        self.assertIn("**pilote** : web/src/doubler.test.ts n'est cité pour aucun critère", trace)
        self.assertIn("**Verdict : NON VALIDÉ**", trace)

    async def test_correction_puis_seconde_execution(self):
        self.cas = "correction"
        self.assertEqual(await self.jouer(), 0)
        self.assertEqual(self.ordre.count("testeur appelé"), 2)
        self.assertEqual(self.ordre.count("code livré"), 1)
        trace = self.lire_trace()
        self.assertIn("correction demandée à redacteur-tests : CA1 impose 6.", trace)
        self.assertIn("**redacteur-tests** : commence : CA1 impose 6.", trace)

    async def test_une_correction_change_quelque_chose(self):
        self.cas = "correction_vide"
        with self.assertRaisesRegex(ValueError, "redacteur-tests n'a livré aucune modification"):
            await self.jouer()

    async def test_relance_du_meme_plan(self):
        """La relance reprend les tests créés par l'essai précédent, livrés ici à l'identique."""
        self.assertEqual(await self.jouer(), 0)
        registre = json.loads((self.racine / pilote.REGISTRE).read_text(encoding="utf-8"))
        self.assertEqual(registre, {"api/tests/test_doubler.py": self.identite(),
                                    "web/src/doubler.test.ts": self.identite()})
        self.charger()
        self.trace = pilote.Trace(self.racine.parent / "relance.md")
        self.trace.ouvrir(self.plan, Path("plan.json"), "pour le test")
        self.assertEqual(await self.jouer(), 0)
        trace = self.lire_trace()
        self.assertIn("developpeur livre ses fichiers à l'identique : rien à écrire", trace)
        self.assertIn("**Verdict : VALIDÉ**", trace)

    async def test_le_registre_precede_les_tests(self):
        """Si le registre ne peut pas être écrit, aucun fichier ne l'est : pas de test orphelin."""
        def echec(*_):
            raise OSError("disque plein")

        with patch.object(pilote, "noter_tests_crees", echec), \
                self.assertRaisesRegex(OSError, "disque plein"):
            await self.jouer()
        for nom in self.plan["code"] + self.plan["tests"]:
            self.assertFalse((self.racine / nom).exists(), nom)

    async def test_livraison_absente(self):
        self.cas = "absente"
        with self.assertRaisesRegex(ValueError, "contrat incomplet"):
            await self.jouer()
        self.assertNotIn("testeur appelé", self.ordre)
        self.assertFalse((self.racine / "api/tests/test_doubler.py").exists())
        self.assertIn("**Verdict : BLOQUÉ : developpeur bloqué : contrat incomplet**",
                      self.lire_trace())

    async def test_le_developpeur_n_ecrit_pas_les_tests(self):
        self.cas = "hors_plan"
        with self.assertRaisesRegex(ValueError, "hors du plan pour developpeur"):
            await self.jouer()
        self.assertFalse((self.racine / "api/app/service.py").exists())

    async def test_session_en_echec(self):
        self.cas = "erreur"
        with self.assertRaises(ExceptionGroup):
            await self.jouer()
        self.assertNotIn("testeur appelé", self.ordre)
        self.assertIn("**developpeur** : termine en", self.lire_trace())

    async def test_trace_complete(self):
        self.assertEqual(await self.jouer(), 0)
        trace = self.lire_trace()
        for attendu in ("- Suite api : `cd api && uv run --locked python -m pytest",
                        "- Suite web : `cd web && npm test --",
                        "**developpeur** : commence : Implémente le plan.",
                        "**redacteur-tests** : commence : Écris les tests du plan.",
                        "écrit api/app/service.py (créé, +2 -0), livré par developpeur",
                        "écrit web/src/doubler.test.ts (créé, +1 -0), livré par redacteur-tests",
                        "```diff",
                        "api : 1 réussis sur 1, code de sortie 0 ; web : 1 réussis sur 1, "
                        "typecheck sans erreur, code de sortie 0",
                        f"CA1 : tests cités, passés, du plan : {TEST_API}",
                        f"CA2 : tests cités, passés, du plan : {TEST_WEB}",
                        "## Bilan",
                        "| Critère | Tests cités par le testeur |",
                        "il ne juge pas s'ils démontrent le critère : relisez-les.",
                        "**Verdict : VALIDÉ**"):
            self.assertIn(attendu, trace)
        self.assertLess(trace.index("écrit api/app/service.py"), trace.index("**testeur** : commence"))


class TestsPlan(Dossier):
    def test_plan_sur_les_deux_dossiers(self):
        self.assertEqual(pilote.suites_du_plan(self.charger()), ["api", "web"])

    def test_cibles_refusees(self):
        cas = {
            "lancer.py": "commence par api/ ou web/",
            "web/src/doubler.js": "extension attendue dans web/",
            "api/app/service.ts": "extension attendue dans api/",
            "web/src/doubler.test.tsx": "fichier de test : sa place est dans tests",
            "api/tests/test_code.py": "fichier de test : sa place est dans tests",
        }
        for cible, message in cas.items():
            with self.subTest(cible=cible), self.assertRaisesRegex(ValueError, message):
                self.charger({**self.plan, "code": [cible]})

    def test_un_test_est_un_fichier_de_test(self):
        with self.assertRaisesRegex(ValueError, "n'est pas un fichier de test"):
            self.charger({**self.plan, "tests": ["api/app/verifier.py"]})

    def test_un_test_existant_reste_dans_le_contexte(self):
        ecrire(self.racine / "api/tests/test_doubler.py", "def test_ancien():\n    pass\n")
        with self.assertRaisesRegex(ValueError, "Test existant : api/tests/test_doubler.py"):
            self.charger()

    def test_la_relance_reprend_les_tests_du_meme_plan(self):
        ecrire(self.racine / "api/tests/test_doubler.py", "def test_ancien():\n    pass\n")
        pilote.noter_tests_crees(self.racine, self.identite(), ["api/tests/test_doubler.py"])
        self.assertEqual(self.charger()["tests"], self.plan["tests"])

    def test_meme_nom_dans_un_autre_dossier(self):
        """autres/plan.json a créé le test : plan.json, de même nom, ne le reprend pas."""
        ecrire(self.racine / "api/tests/test_doubler.py", "def test_ancien():\n    pass\n")
        pilote.noter_tests_crees(self.racine, self.identite("autres/plan.json"),
                                 ["api/tests/test_doubler.py"])
        with self.assertRaisesRegex(ValueError, "ne vient pas d'un essai de ce plan"):
            self.charger()

    def test_plan_modifie_entre_deux_essais(self):
        ecrire(self.racine / "api/tests/test_doubler.py", "def test_ancien():\n    pass\n")
        pilote.noter_tests_crees(self.racine, self.identite(), ["api/tests/test_doubler.py"])
        modifie = {**self.plan, "criteres": {"CA1": "doubler(4) vaut 8 côté API",
                                             "CA2": "doubler(3) vaut 6 côté interface"}}
        with self.assertRaisesRegex(ValueError, "version précédente de ce plan"):
            self.charger(modifie)

    def test_registre_perdu_ou_illisible(self):
        """Sans registre lisible, le pilote ne croit aucun test sien : il refuse de le réécrire."""
        ecrire(self.racine / "api/tests/test_doubler.py", "def test_ancien():\n    pass\n")
        pilote.noter_tests_crees(self.racine, self.identite(), ["api/tests/test_doubler.py"])
        registre = self.racine / pilote.REGISTRE
        for contenu in (None, "{ illisible", "[]"):
            with self.subTest(contenu=contenu):
                if contenu is None:
                    registre.unlink()
                else:
                    ecrire(registre, contenu)
                with self.assertRaisesRegex(ValueError, "ne vient pas d'un essai de ce plan"):
                    self.charger()

    def test_contexte_sans_secret_ni_binaire(self):
        ecrire(self.racine / "api/.env", "OPENAI_API_KEY=sk-test\n")
        (self.racine / "api/portail.db").write_bytes(b"SQLite format 3\x00\xff\xfe")
        for nom, message in {"api/.env": "jamais de fichier .env",
                             "api/portail.db": "que des fichiers texte"}.items():
            with self.subTest(nom=nom), self.assertRaisesRegex(ValueError, message):
                self.charger({**self.plan, "contexte": [nom]})


class TestsProfils(unittest.TestCase):
    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.profils = Path(dossier.name)
        remplacement = patch.object(pilote, "PROFILS", self.profils)
        remplacement.start()
        self.addCleanup(remplacement.stop)
        outils = {pilote.DEV: "[read, search, edit]", pilote.REDACTEUR: "['read', 'search', 'edit']",
                  pilote.TESTEUR: "\n  - read\n  - search\n  - execute"}
        for role, liste in outils.items():
            self.ecrire(role, PROFIL.format(role=role, outils=liste))

    def ecrire(self, role, texte):
        ecrire(self.profils / f"{role}.agent.md", texte)

    def test_profils_complets(self):
        profils = pilote.verifier_profils()
        self.assertEqual(profils[pilote.TESTEUR][0], ["read", "search", "execute"])
        self.assertEqual(profils[pilote.REDACTEUR][0], ["read", "search", "edit"])
        self.assertEqual(profils[pilote.DEV][1], "Consignes de test pour developpeur.")

    def test_profil_absent(self):
        (self.profils / "testeur.agent.md").unlink()
        with self.assertRaisesRegex(FileNotFoundError, "testeur.agent.md"):
            pilote.verifier_profils()

    def test_profil_encore_a_ecrire(self):
        self.ecrire(pilote.DEV, PROFIL.format(role=pilote.DEV, outils="[read]") + "\nÀ écrire\n")
        with self.assertRaisesRegex(ValueError, "Profil developpeur encore à écrire"):
            pilote.verifier_profils()

    def test_nom_different_du_fichier(self):
        self.ecrire(pilote.DEV, PROFIL.format(role="dev", outils="[read]"))
        with self.assertRaisesRegex(ValueError, "name doit valoir developpeur"):
            pilote.verifier_profils()

    def test_le_testeur_doit_pouvoir_executer(self):
        self.ecrire(pilote.TESTEUR, PROFIL.format(role=pilote.TESTEUR, outils="[read, search]"))
        with self.assertRaisesRegex(ValueError, "testeur doit déclarer l'outil execute"):
            pilote.verifier_profils()

    def test_seul_le_testeur_execute(self):
        self.ecrire(pilote.REDACTEUR, PROFIL.format(role=pilote.REDACTEUR,
                                                    outils="[read, execute/runInTerminal]"))
        with self.assertRaisesRegex(ValueError, "redacteur-tests déclare execute"):
            pilote.verifier_profils()

    def test_profils_lus_dans_le_lab_seulement(self):
        """Un profil du dossier parent, comme ceux de la démo 5, n'est jamais repris."""
        self.assertEqual(PROFILS_DU_LAB, pilote.RACINE / ".github" / "agents")
        lab = self.profils / "lab" / ".github" / "agents"
        with patch.object(pilote, "PROFILS", lab), \
                self.assertRaisesRegex(FileNotFoundError, "developpeur.agent.md"):
            pilote.lire_profil(pilote.DEV)


class TestsLecture(unittest.TestCase):
    def test_pytest(self):
        sortie = ("PASSED tests/test_a.py::test_un\nFAILED tests/test_a.py::test_deux\n"
                  "========= 1 failed, 1 passed in 0.12s =========\n")
        self.assertEqual(pilote.passes_pytest(sortie), {"api::tests/test_a.py::test_un"})
        self.assertEqual(pilote.resume_pytest(sortie), "1 réussis sur 2 (en échec : 1)")

    def test_vitest(self):
        web = Path("/projet/web")
        donnees = {"numTotalTests": 2, "numPassedTests": 1, "numFailedTests": 1,
                   "testResults": [{"name": "/projet/web/src/App.test.tsx", "assertionResults": [
                       {"status": "passed", "ancestorTitles": ["App"], "title": "affiche"},
                       {"status": "failed", "ancestorTitles": ["App"], "title": "filtre"}]}]}
        passes, resume = pilote.lire_vitest(donnees, web)
        self.assertEqual(passes, {"web::src/App.test.tsx > App > affiche"})
        self.assertEqual(resume, "1 réussis sur 2 (en échec : 1)")


if __name__ == "__main__":
    unittest.main()
