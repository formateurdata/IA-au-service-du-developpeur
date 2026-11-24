# Jour 1 - Demo 3 bis : un agent relecteur cree avec /create-agent

**Apres la diapositive 19 (demo 3).** Se joue dans VS Code avec Copilot Chat,
sans script. Il faut VS Code 1.110 ou plus recent.

## Le materiel

- `projet/` : le dossier a ouvrir dans VS Code. `validateur_email.py` est
  correct. `test_validateur_email.py` contient six tests, tous verts, dont
  quatre trop faibles.
- `relecteur-pytest.agent.md` : le profil de secours, si `/create-agent`
  n'est pas disponible.

## Deroule

**0. Les tests passent.** Ouvrir le dossier `projet` lui-meme dans VS Code
(Fichier > Ouvrir le dossier), puis dans le terminal :

```bash
uv run pytest      # 6 passed
```

Demander au groupe : « Les tests passent, donc le code est bon ? »

**1. Creer l'agent.** Copilot Chat, mode Agent :

```text
/create-agent Crée un agent de projet nommé relecteur-pytest.

Sa mission : relire du code Python et ses tests pytest, et trouver les tests
trop faibles. Pour chacun, il donne une modification du code qui introduit un
bug en laissant toute la suite au vert, puis l'assertion qui détecterait ce bug.
Il termine par les règles de la docstring qu'aucun test ne vérifie.

Donne-lui uniquement les outils de lecture et de recherche.
Il utilise le modèle Claude Sonnet 5.5.
Enregistre-le dans l'espace de travail, dans .github/agents/.
```

Si la commande pose des questions (espace de travail ou utilisateur), choisir
l'espace de travail.

**2. Relire ce qui a ete genere.** Ouvrir
`.github/agents/relecteur-pytest.agent.md` et lire la ligne `tools:`. Elle
doit valoir `['read', 'search']`. Si elle contient `edit`, `execute` ou `*`,
la corriger devant le groupe : la configuration d'un agent generee par l'IA
se relit, comme son code.

Lire aussi la ligne `model:`. Elle doit valoir `claude-sonnet-5.5`,
l'identifiant de Copilot, et non le nom affiche « Claude Sonnet 5.5 ». Pour le
verifier ou le corriger, taper `model: ` dans l'en-tete et choisir le modele
dans la completion de l'editeur. Choisir l'agent bascule alors la
conversation sur ce modele. S'il n'est pas disponible sur le poste, Copilot en
prend un autre : verifier le modele affiche dans le selecteur.

**3. Utiliser l'agent.** Nouvelle conversation, choisir `relecteur-pytest`
dans le menu des agents, puis une seule phrase :

```text
Relis les tests du validateur d'e-mail.
```

**4. Prouver ce qu'il affirme.** Prendre un bug qu'il propose, de preference
« refuser toutes les adresses ». Le coller dans `validateur_email.py`,
relancer `uv run pytest` : toujours 6 tests verts. Annuler la modification.
Ce que dit l'agent est prouve par une execution, pas cru sur parole.

**5. La limite de permission.** Dans la meme conversation :

```text
Corrige toi-même le test test_adresse_valide.
```

Sans outil d'ecriture, l'agent ne peut que proposer la modification. Le
panneau Git ne montre aucun fichier modifie.

## Ce qu'il faut faire remarquer

1. **Une suite verte ne prouve rien par elle-meme.** Un validateur qui refuse
   toutes les adresses passe les six tests : aucun ne prouve qu'une adresse
   valide est acceptee.
2. **Le profil se versionne.** `.github/agents/` est dans le depot : toute
   l'equipe relit avec la meme methode, en une phrase.
3. **Retirer une permission est plus fiable qu'ecrire une consigne**
   (diapositive 17). Le relecteur ne modifie rien parce qu'il n'a pas l'outil
   d'ecriture, pas parce qu'on le lui a demande.
4. **Le lien avec le Lab 1, etape 5** : un test qui ne peut pas echouer ne
   prouve rien.

## Corrige

Chacun de ces bugs laisse les six tests verts. L'assertion de la derniere
colonne le detecte.

| Test faible | Bug qui reste au vert | Assertion qui le detecte |
|---|---|---|
| `test_adresse_valide` : un dictionnaire non vide est toujours vrai | refuser toutes les adresses : `return {"valide": False, "raison": "adresse refusée"}` en premiere ligne | `assert valider_email("alice@example.fr") == {"valide": True, "raison": None}` |
| `test_trop_longue` : 311 caracteres, loin de la limite | `LONGUEUR_MAX = 300` | 254 caracteres acceptes (`"a" * 243 + "@example.fr"`), 255 refuses (`"a" * 244 + ...`) |
| `test_espaces` : seul l'espace en debut est teste | `valeur.lstrip()` au lieu de `valeur.strip()` | `assert valider_email("alice@example.fr ")["valide"] is False` |
| Aucun test ne verifie la raison | une mauvaise raison, par exemple « il faut exactement un arobase » pour un domaine sans point | `assert valider_email("alice@example")["raison"] == "domaine sans point"` |

Si l'agent n'en trouve que deux ou trois, completer avec ce tableau : un
relecteur IA rate aussi des choses, c'est le test qui prouve. S'il propose un
autre bug, le verifier de la meme facon, en relancant les tests.

## A verifier la veille

- `/create-agent` apparait dans le menu `/` de Copilot Chat. Sinon, passer
  par la commande « Chat: New Custom Agent », choisir l'espace de travail, et
  coller le contenu de `relecteur-pytest.agent.md`.
- `uv sync` a la racine de la formation installe pytest. Puis, depuis
  `projet/` : `uv run pytest` affiche 6 passed.
- Apres la repetition, supprimer `projet/.github/` : sinon l'agent existe deja
  et la creation en direct echoue. Ce dossier est ignore par git.
