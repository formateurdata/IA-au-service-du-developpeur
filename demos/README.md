# Demonstrations - Formation DEIA

Les dix demonstrations des deux jours, faites ensemble en salle, et le
materiel de l'exercice en binome du Jour 1 sur les hallucinations.

## Principe : rien ne doit dependre du reseau en salle

Chaque demo scriptee a deux modes.

| Mode | Commande | Ce qu'il fait |
|---|---|---|
| Repetition | `python3 <script>.py` | rejoue une sortie enregistree, sans uv, sans reseau ni cle |
| Direct | `uv run <script>.py --live` | appelle reellement le service |
| Enregistrement | `uv run <script>.py --live --enregistrer` | appelle et fige la sortie |

**Aucune sortie n'est fournie prete a l'emploi.** Elles sont produites par
votre propre repetition, pour que ce qui est projete corresponde a ce que
votre environnement produit reellement, avec votre cle et votre modele.

C'est aussi ce qui garantit le plan B annonce dans les notes du presentateur
de chaque diapositive de demo.

## Mise en route

Une seule installation, a la racine de la formation (le dossier qui contient
`pyproject.toml`) : `uv sync` cree `.venv/` avec toutes les dependances des
demos, versions figees par `uv.lock`, sous Python 3.12 (`.python-version`,
telecharge au besoin). Ensuite, `uv run` lance chaque script dans cet
environnement, depuis n'importe quel sous-dossier.

```bash
uv sync                       # a la racine ; a refaire si un git pull modifie uv.lock
cd demos
cp .env.example .env          # puis y coller la cle de session
uv run verifier-environnement.py
```

Les labs n'utilisent pas cet environnement : chacun a le sien, dans son
dossier `api/`, installe par `uv run lancer.py`.

Le mode repetition n'a aucune dependance : il tourne avec un `python3` nu
(Windows : `py`), sans reseau. C'est pourquoi le jour J on le lance avec
`python3` : il marche meme si `.venv/` est absent ou incomplet sur le poste
de projection.

`verifier-environnement.py` affiche ce qui est installe, si la cle est
disponible, et quelles demos disposent deja de leur plan B. **A relancer la
veille de chaque session.**

## Preparer tous les plans B en une passe

```bash
cd j1/demo1-tokenisation       && uv run tokenisation.py "calculTotalHT_v2"    && cd ../..
cd j1/demo1-tokenisation       && uv run tokenisation.py --enc o200k_base "x"  && cd ../..
cd j2/demo1-appel-api          && uv run appel_brut.py     --live --enregistrer && cd ../..
cd j2/demo2-langchain-template && uv run template_chain.py --live --enregistrer && cd ../..
cd j2/demo3-similarite         && uv run similarite.py     --live --enregistrer && cd ../..
cd j2/demo4-image              && uv run generer_image.py  --live               && cd ../..
uv run verifier-environnement.py
```

La demo de tokenisation n'enregistre rien, elle a besoin de tiktoken. Ses deux
lancements telechargent les deux encodages dans
`j1/demo1-tokenisation/cache-tiktoken/`. Le jour J, `uv run --offline` la fait
tourner sans aucun acces reseau ; `verifier-environnement.py` le teste.

## Jour 1

Numeros de diapositive de `DEIA_Jour1_v2.pptx`.

| Demo | Diapo | Dossier |
|---|---|---|
| 1. Tokenisation | 10 | `j1/demo1-tokenisation/` |
| 2. ChatGPT contre Copilot | 15 | `j1/demo2-chatgpt-vs-copilot/` |
| 3. Generer sans puis avec des regles | 19 | `j1/demo3-cadrage/` |
| 3 bis. Un agent relecteur cree avec /create-agent | apres 19 | `j1/demo3bis-agent-relecteur/` |
| 4. Provoquer une hallucination | 24 | `j1/demo4-hallucination/` |
| Exercice en binome | 27 | `j1/demo4-hallucination/` |

Les demos 2, 3, 3 bis et 4 se jouent dans l'editeur ou dans un assistant,
sans script. La demo 4 et l'exercice partagent `Demo_Hallucinations.pdf` et les
deux documents longs de `j1/demo4-hallucination/materiel/` : le journal des
comites de pilotage du portail et les journaux de son API. La fiche donne les
questions a poser, le reglage de l'outil, la parade et les reponses, calculees
sur les fichiers.

## Jour 2

| Demo | Diapo | Dossier | Prepare |
|---|---|---|---|
| 1. Appel API brut | 7 | `j2/demo1-appel-api/` | Lab 2, etape 1 |
| 2. Prompt template LangChain | 10 | `j2/demo2-langchain-template/` | Lab 2 et Lab 3 |
| 3. Recherche par similarite | 16 | `j2/demo3-similarite/` | Lab 3 |
| 4. Prompt court contre detaille | 25 | `j2/demo4-image/` | - |
| 5. Un systeme agentique : quatre agents | - | `j2/demo5-systeme-agentique/` | Lab 4 |

La demo 5 se joue dans VS Code avec Copilot Chat, sans plan B enregistre.
Ses quatre agents sont dans `.github/agents/` a la racine de la formation :
ouvrir la racine dans VS Code pour les voir.

`j2/corpus/` contient six procedures internes fictives. Il sert a la demo 3
**et** au Lab 3, a l'identique : les participants retrouveront les memes
documents, ce qui leur evite de decouvrir l'outil et les donnees en meme temps.

## Cinq demos a retester imperativement avant chaque session

**Jour 1, demo 4 (hallucination).** Les modeles evoluent : une question qui
piegeait le modele il y a six mois peut aujourd'hui recevoir une reponse
correcte. Passer les questions de la fiche avec l'outil et le modele de la
session, noter celles qui echouent, et garder sous la main les leviers de la
section 6 de la fiche (comparer les postes, allonger le contexte).

**Jour 1, demo 3 (cadrage).** Verifier que la version installee de
l'extension Copilot prend bien en compte `AGENTS.md`. Sinon, renommer le
fichier en `.github/copilot-instructions.md` : meme contenu, meme effet,
convention plus ancienne et plus largement supportee.

**Jour 1, demo 3 bis (agent relecteur).** Verifier que `/create-agent` est
disponible dans Copilot Chat, et supprimer `projet/.github/` apres la
repetition : voir `j1/demo3bis-agent-relecteur/README.md`.

**Jour 2, demo 4 (image).** Verifier que le modele d'image du script est
toujours disponible : voir `j2/demo4-image/README.md`.

**Jour 2, demo 5 (systeme agentique).** Verifier que Copilot CLI est
authentifie (`copilot login`) et lancer le pilote une fois la veille, avec le
reseau : le premier lancement telecharge le SDK. Remettre `projet/` a zero
ensuite : voir `j2/demo5-systeme-agentique/README.md`.

## Ce que ce dossier ne contient pas

Les travaux pratiques. Ils sont dans `../lab/` : chaque lab contient son
enonce en PDF et l'application de depart. Les demos preparent les labs, elles
ne les remplacent pas.
