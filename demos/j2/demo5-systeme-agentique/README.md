# Jour 2 - Demo 5 : un systeme agentique, quatre agents et un pilote Python

**Prepare le Lab 4.** Se joue dans VS Code avec Copilot Chat. Les quatre
agents sont dans `.github/agents/` a la racine de la formation : ouvrir la
**racine de la formation** dans VS Code, pas le dossier `projet/`, sinon
l'orchestrateur n'apparait pas dans le menu des agents.

## Le materiel

- `projet/` : une API FastAPI qui reprend le portail des labs.
  `GET /api/demandes` renvoie trois demandes ; le filtre par statut est la
  fonctionnalite que l'equipe d'agents developpe pendant la seance.
  `app/modeles.py` definit deja le type `Statut`.
- `projet/pilote.py` : le pilote Python. Apres l'accord donne a
  l'orchestrateur, il conduit les trois specialistes par le SDK Copilot.
- `projet/plan-exemple.json` : le plan de reference, cinq criteres.
- `projet/verification/` : le pilote teste avec des doubles de sessions,
  sans compte Copilot.
- `.github/agents/` (racine) : `orchestrateur`, seul visible dans le menu,
  et les trois specialistes `developpeur`, `redacteur-tests`, `testeur`.

| Agent | Recoit | Livre | Outils sous le pilote |
|---|---|---|---|
| orchestrateur | la demande et le projet | le plan approuve, puis le lancement du pilote | lecture, ecriture, terminal (dans VS Code) |
| developpeur | le contrat et les sources du plan | les fichiers de production complets | aucun |
| redacteur-tests | le meme contrat, les memes sources | les tests de comportement | aucun |
| testeur | les fichiers livres et les criteres | une preuve par critere, un diagnostic | `executer_pytest`, rien d'autre |

## Deroule

**0. Le depart.** Dans le terminal de VS Code :

```bash
cd demos/j2/demo5-systeme-agentique/projet
uv run pytest          # 1 passed
```

**1. Demander un plan.** Nouvelle conversation Copilot Chat, choisir
`orchestrateur` dans le menu des agents :

```text
Sur ce projet FastAPI, ajoute à GET /api/demandes un filtre de statut facultatif. Inspecte l'implémentation et les tests déjà présents. Propose un plan de code et un plan de tests avec les critères d'acceptation, puis attends ma validation.
```

L'orchestrateur lit le projet et propose un contrat, des criteres CA1 a CA5,
deux missions et leurs fichiers. Le comparer a `plan-exemple.json`. Rien
n'est encore modifie : il attend l'accord.

**2. Valider et lancer.**

```text
Je valide ce plan. Enregistre-le et déclenche le pipeline Python. Montre-moi les livraisons et le résultat par critère.
```

Il ecrit `.copilot-plans/filtre-statut.json`, puis lance le pilote dans le
terminal integre ; VS Code peut demander l'autorisation. Chaque ligne du
journal porte l'heure, le temps ecoule et l'acteur. Dans l'ordre :

1. `developpeur` et `redacteur-tests` : `commence`, ensemble, puis
   `termine en ... : livre ...` ;
2. `pilote` : livraisons controlees, puis `écrit app/main.py (modifié, +5 -2)`
   pour chaque fichier ;
3. `testeur` : `commence`, puis la commande pytest et sa sortie reelle ;
4. `pilote` : une ligne par critere avec le test qui le prouve ;
5. le `BILAN` : une ligne par session d'agent (heures, duree, fichiers
   ecrits), les tests (`réussis : 11 sur 11`), le verdict, puis
   `Trace complète : traces/<horodatage>-filtre-statut.md`.

L'orchestrateur reprend ce bilan dans le chat, avec un lien et le diff pour
chaque fichier ecrit.

**3. Ouvrir la trace.** `projet/traces/<horodatage>-filtre-statut.md`, en
apercu Markdown : la chronologie complete. Sous chaque evenement, des blocs
repliables donnent la consigne recue par l'agent, le diff du fichier ecrit,
la sortie pytest et le rapport brut du testeur. La trace est ecrite au fil de
l'eau : apres un `BLOQUÉ`, elle montre ou et pourquoi le pilote s'est arrete.

**4. Lire le diff.** Panneau Git : `app/main.py` modifie, un fichier de tests
cree. Verifier que le developpeur a reutilise `Statut` au lieu de recopier
les quatre valeurs, et que le 422 vient du type, pas d'un `if`.

## Ce qu'il faut faire remarquer

1. **Le plan avant le code.** L'humain valide un contrat et des criteres
   verifiables ; aucun agent n'ecrit avant cet accord.
2. **Deux agents en parallele, une synchronisation deterministe.**
   `asyncio.TaskGroup` attend les deux livraisons. Python verifie ensuite les
   chemins autorises, la syntaxe, et que les fichiers du plan n'ont pas bouge
   entre-temps. Une livraison refusee, vide ou hors perimetre bloque tout :
   le testeur n'est jamais appele sur un etat incomplet.
3. **Le testeur ne peut pas mentir sur l'execution.** Il n'a qu'un outil,
   `executer_pytest`. S'il repond sans l'appeler, le pilote s'arrete. S'il
   cite un test absent des `PASSED` de la sortie reelle, le critere devient
   « preuve absente » et le verdict `NON VALIDÉ`, meme avec une suite verte.
4. **Les permissions par construction** (diapositive 17, demo 3 bis du
   jour 1). Le developpeur et le redacteur n'ont aucun outil ; toute demande
   de permission est refusee par le pilote. Ils ne peuvent que proposer des
   fichiers, que Python valide et ecrit.
5. **Une boucle bornee.** Un defaut attribue repart vers le specialiste
   concerne, deux corrections au maximum. C'est la parade a la consommation
   non bornee vue dans la partie securite.

## Jouer le plan sans le chat

Depuis `projet/` :

```bash
uv run --script pilote.py --plan plan-exemple.json
```

Le script affiche le plan et demande `oui`. L'option `--approuve` saute la
question : elle est reservee au plan deja valide dans le chat.

## Verifier le pilote sans compte Copilot

Depuis `projet/` :

```bash
uv run --locked --group orchestration python -m unittest discover -s verification
```

Huit tests. Six scenarios avec des doubles de sessions : l'ordre des
livraisons, un refus de livrer, une session en erreur, l'obligation de lancer
pytest, une preuve inventee, une correction suivie d'une seconde execution.
Ceux qui vont jusqu'a l'execution lancent vraiment pytest dans un projet
temporaire. Un septieme verifie le contenu de la trace, un huitieme que le
pilote trouve les trois profils dans `.github/agents/` a la racine de la
formation.

## Remettre a zero apres la repetition

Depuis `projet/` :

```bash
git restore app/main.py
rm -rf .copilot-plans tests/test_filtre_statut.py
git status .           # rien d'autre ne doit apparaitre
```

Si le plan valide en seance a nomme un autre fichier de tests, `git status`
le montre : le supprimer aussi.

## A verifier la veille

- Copilot CLI authentifie avec un compte qui a acces a Copilot :
  `copilot login`. Sans cela, le pilote s'arrete sur `BLOQUÉ`.
- Le premier `uv run --script pilote.py` telecharge le SDK et prepare son
  runtime : le faire la veille, avec le reseau, puis remettre a zero.
- `uv sync` dans `projet/`, puis `uv run pytest` : 1 passed.
- La verification ci-dessus : 8 tests OK.
- Dans le menu des agents de Copilot Chat, `orchestrateur` apparait et les
  trois specialistes n'apparaissent pas.
