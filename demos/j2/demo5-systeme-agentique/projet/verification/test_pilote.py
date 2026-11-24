"""Tests de la coordination avec doubles de sessions et un véritable processus pytest."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pilote

TEST_ANCIEN = "tests/test_ancien.py::test_ancien"


def ecrire(chemin, texte):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(texte, encoding="utf-8")


class Projet:
    """Un projet minimal dans un dossier temporaire, et son plan."""

    def preparer(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.base = Path(dossier.name).resolve()
        self.racine = self.base / "projet"
        self.racine.mkdir()
        self.plan = {"objectif": "Doubler la valeur", "criteres": {"CA1": "doubler(3) vaut 6"},
                     "code": ["src/service.py"], "tests": ["tests/test_doubler.py"],
                     "contexte": []}

    def charger(self, plan=None):
        chemin = self.racine / "plan.json"
        ecrire(chemin, json.dumps(plan or self.plan, ensure_ascii=False))
        return pilote.charger_plan(self.racine, chemin)

    def identite(self, chemin="plan.json", plan=None):
        return pilote.identite_plan(self.racine, self.racine / chemin, plan or self.plan)


class TestsPipeline(Projet, unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.preparer()
        base = self.base
        self.ordre = []
        self.cas = "ok"
        self.appels = 0
        self.commande = [sys.executable, "-m", "pytest", "-v", "--tb=short", "-rA", "--color=no"]
        self.trace = pilote.Trace(base / "trace.md")
        self.trace.ouvrir(self.plan, Path("plan.json"), self.commande, "pour le test")

    async def agent(self, client, racine, role, message, outils=()):
        if role == pilote.DEV:
            await asyncio.sleep(0.025)
            if self.cas == "erreur":
                raise RuntimeError("session interrompue")
            self.ordre.append("code livré")
            if self.cas == "absente":
                return {"statut": "bloque", "raison": "contrat incomplet"}
            return {"statut": "livre",
                    "fichiers": {"src/service.py": "def doubler(x):\n    return 2*x\n"}}
        if role == pilote.REDACTEUR:
            self.ordre.append("tests livrés")
            self.appels += 1
            attendu = 7 if self.cas == "correction" and self.appels == 1 else 6
            test = ("from src.service import doubler\n\n"
                    f"def test_doubler():\n    assert doubler(3) == {attendu}\n")
            return {"statut": "livre", "fichiers": {"tests/test_doubler.py": test}}
        self.ordre.append("testeur appelé")
        self.assertTrue((racine / "src/service.py").is_file())
        self.assertTrue((racine / "tests/test_doubler.py").is_file())
        if self.cas != "inventee":
            resultat = await outils[0].handler(None)
            execution = json.loads(resultat.text_result_for_llm)
            if self.cas == "correction" and execution["code_sortie"] == 1:
                return {"preuves": {}, "corrections": {pilote.REDACTEUR: "CA1 impose 6."}}
            if self.cas == "correction_vide":
                return {"preuves": {}, "corrections": {pilote.REDACTEUR: "Renomme le test."}}
        test = {"non_observee": "test_invente", "hors_plan_preuve": TEST_ANCIEN}.get(
            self.cas, "tests/test_doubler.py::test_doubler")
        return {"preuves": {"CA1": [test]}, "corrections": {}}

    async def jouer(self):
        with patch.object(pilote, "demander", self.agent):
            return await pilote.pipeline(None, self.racine, self.plan, self.commande, self.trace,
                                         self.identite())

    def lire_trace(self):
        return self.trace.chemin.read_text(encoding="utf-8")

    async def test_deux_livraisons_avant_le_vrai_pytest(self):
        self.assertEqual(await self.jouer(), 0)
        self.assertEqual(self.ordre, ["tests livrés", "code livré", "testeur appelé"])

    async def test_livraison_absente(self):
        self.cas = "absente"
        with self.assertRaisesRegex(ValueError, "contrat incomplet"):
            await self.jouer()
        self.assertNotIn("testeur appelé", self.ordre)
        self.assertFalse((self.racine / "tests/test_doubler.py").exists())
        self.assertIn("**Verdict : BLOQUÉ : developpeur bloqué : contrat incomplet**",
                      self.lire_trace())

    async def test_session_en_echec(self):
        self.cas = "erreur"
        with self.assertRaises(ExceptionGroup):
            await self.jouer()
        self.assertNotIn("testeur appelé", self.ordre)
        self.assertIn("**developpeur** : termine en", self.lire_trace())

    async def test_le_testeur_doit_lancer_pytest(self):
        self.cas = "inventee"
        with self.assertRaisesRegex(ValueError, "sans exécuter"):
            await self.jouer()

    async def test_preuve_non_observee(self):
        self.cas = "non_observee"
        self.assertEqual(await self.jouer(), 1)
        self.assertIn("**pilote** : CA1 : preuve refusée : test_invente ne figure pas parmi les "
                      "tests passés", self.lire_trace())

    async def test_une_preuve_vient_d_un_test_du_plan(self):
        """Un test passé, mais d'un autre fichier, ne prouve pas un critère de ce plan."""
        ecrire(self.racine / "tests/test_ancien.py", "def test_ancien():\n    pass\n")
        self.cas = "hors_plan_preuve"
        self.assertEqual(await self.jouer(), 1)
        trace = self.lire_trace()
        self.assertIn(f"**pilote** : CA1 : preuve refusée : {TEST_ANCIEN} n'est pas un test de ce "
                      "plan", trace)
        self.assertIn("**pilote** : tests/test_doubler.py n'est cité pour aucun critère", trace)
        self.assertIn("**Verdict : NON VALIDÉ**", trace)

    async def test_une_correction_change_quelque_chose(self):
        self.cas = "correction_vide"
        with self.assertRaisesRegex(ValueError, "redacteur-tests n'a livré aucune modification"):
            await self.jouer()

    async def test_relance_du_meme_plan(self):
        """La relance reprend le test créé par l'essai précédent, livré ici à l'identique."""
        self.assertEqual(await self.jouer(), 0)
        registre = json.loads((self.racine / pilote.REGISTRE).read_text(encoding="utf-8"))
        self.assertEqual(registre, {"tests/test_doubler.py": self.identite()})
        self.charger()
        self.trace = pilote.Trace(self.base / "relance.md")
        self.trace.ouvrir(self.plan, Path("plan.json"), self.commande, "pour le test")
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

    async def test_correction_puis_seconde_execution_complete(self):
        self.cas = "correction"
        self.assertEqual(await self.jouer(), 0)
        self.assertEqual(self.ordre.count("testeur appelé"), 2)
        self.assertEqual(self.ordre.count("code livré"), 1)
        trace = self.lire_trace()
        self.assertIn("correction demandée à redacteur-tests : CA1 impose 6.", trace)
        self.assertIn("**redacteur-tests** : commence : CA1 impose 6.", trace)

    async def test_trace_complete(self):
        self.assertEqual(await self.jouer(), 0)
        trace = self.lire_trace()
        for attendu in ("**developpeur** : commence : Implémente le plan.",
                        "**redacteur-tests** : commence : Écris les tests du plan.",
                        "**developpeur** : termine en",
                        "écrit src/service.py (créé, +2 -0), livré par developpeur",
                        "écrit tests/test_doubler.py (créé, +4 -0), livré par redacteur-tests",
                        "```diff",
                        "réussis : 1 sur 1",
                        "CA1 : tests cités, passés, du plan : tests/test_doubler.py::test_doubler",
                        "## Bilan",
                        "| Critère | Tests cités par le testeur |",
                        "il ne juge pas s'ils démontrent le critère : relisez-les.",
                        "**Verdict : VALIDÉ**"):
            self.assertIn(attendu, trace)
        self.assertLess(trace.index("écrit src/service.py"), trace.index("**testeur** : commence"))


class TestsPlan(Projet, unittest.TestCase):
    def setUp(self):
        self.preparer()
        ecrire(self.racine / "tests/test_doubler.py", "def test_ancien():\n    pass\n")

    def test_un_test_existant_reste_dans_le_contexte(self):
        with self.assertRaisesRegex(ValueError, "Test existant : tests/test_doubler.py"):
            self.charger()

    def test_la_relance_reprend_les_tests_du_meme_plan(self):
        pilote.noter_tests_crees(self.racine, self.identite(), ["tests/test_doubler.py"])
        self.assertEqual(self.charger()["tests"], self.plan["tests"])

    def test_meme_nom_dans_un_autre_dossier(self):
        """autres/plan.json a créé le test : plan.json, de même nom, ne le reprend pas."""
        pilote.noter_tests_crees(self.racine, self.identite("autres/plan.json"),
                                 ["tests/test_doubler.py"])
        with self.assertRaisesRegex(ValueError, "ne vient pas d'un essai de ce plan"):
            self.charger()

    def test_plan_modifie_entre_deux_essais(self):
        pilote.noter_tests_crees(self.racine, self.identite(), ["tests/test_doubler.py"])
        modifie = {**self.plan, "criteres": {"CA1": "doubler(4) vaut 8"}}
        with self.assertRaisesRegex(ValueError, "version précédente de ce plan"):
            self.charger(modifie)

    def test_registre_perdu_ou_illisible(self):
        """Sans registre lisible, le pilote ne croit aucun test sien : il refuse de le réécrire."""
        pilote.noter_tests_crees(self.racine, self.identite(), ["tests/test_doubler.py"])
        registre = self.racine / pilote.REGISTRE
        for contenu in (None, "{ illisible", "[]"):
            with self.subTest(contenu=contenu):
                if contenu is None:
                    registre.unlink()
                else:
                    ecrire(registre, contenu)
                with self.assertRaisesRegex(ValueError, "ne vient pas d'un essai de ce plan"):
                    self.charger()


class TestsProfils(unittest.TestCase):
    def test_les_trois_profils_sont_trouves(self):
        for role in (pilote.DEV, pilote.REDACTEUR, pilote.TESTEUR):
            corps = pilote.definition_agent(role).split("---", 2)[2].strip()
            self.assertTrue(corps, role)
