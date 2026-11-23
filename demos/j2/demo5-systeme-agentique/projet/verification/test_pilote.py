"""Tests de la coordination avec doubles de sessions et un véritable processus pytest."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pilote


class TestsPipeline(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        base = Path(dossier.name).resolve()
        self.racine = base / "projet"
        self.racine.mkdir()
        self.plan = {"objectif": "Doubler la valeur", "criteres": {"CA1": "doubler(3) vaut 6"},
                     "code": ["src/service.py"], "tests": ["tests/test_doubler.py"],
                     "contexte": []}
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
        test = "tests/test_doubler.py::test_doubler"
        return {"preuves": {"CA1": [test if self.cas != "non_observee" else "test_invente"]},
                "corrections": {}}

    async def jouer(self):
        with patch.object(pilote, "demander", self.agent):
            return await pilote.pipeline(None, self.racine, self.plan, self.commande, self.trace)

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
        self.assertIn("**pilote** : CA1 : preuve absente", self.lire_trace())

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
                        "CA1 : prouvé par tests/test_doubler.py::test_doubler",
                        "## Bilan",
                        "**Verdict : VALIDÉ**"):
            self.assertIn(attendu, trace)
        self.assertLess(trace.index("écrit src/service.py"), trace.index("**testeur** : commence"))


class TestsProfils(unittest.TestCase):
    def test_les_trois_profils_sont_trouves(self):
        for role in (pilote.DEV, pilote.REDACTEUR, pilote.TESTEUR):
            corps = pilote.definition_agent(role).split("---", 2)[2].strip()
            self.assertTrue(corps, role)
