# Jour 2 - Demo 3 : un RAG qui repond, ou qui dit qu'il ne sait pas

**Diapositive 16.** C'est la demo qui rend le RAG concret.

```bash
uv run similarite.py --live --enregistrer   # avant la session : enregistre les trois modes
python3 similarite.py                       # le jour J : recherche hybride
python3 similarite.py --mode semantique     # le jour J : par le sens seul
python3 similarite.py --mode lexicale       # le jour J : par les mots seuls (BM25)
```

`--mode` fonctionne aussi avec `--live` : seul le mode demande est alors calcule.

## Le dispositif

Le corpus (`../corpus/`, six procedures internes fictives) est decoupe comme
au Lab 3, en morceaux de 800 caracteres, puis interroge avec cinq questions
reprises du jeu de reference du Lab 3 :

| Question | La reponse est-elle dans les procedures ? |
|---|---|
| Combien de temps puis-je rester chez moi pour bosser ? | oui : trois jours par semaine (PR-014), sans un seul mot commun avec la question |
| Quel est le montant maximum rembourse pour dormir a l'hotel a Paris ? | oui : 160 euros (PR-021) |
| Que dit la procedure PR-045 ? | oui : c'est l'astreinte technique |
| Combien de jours de conge sont accordes pour un mariage ? | non |
| Quel est le montant de la prime de cooptation ? | non |

Pour chaque question, le script affiche les passages retrouves, puis la
reponse du modele. Le modele (gpt-4o-mini) recoit la consigne du corrige du
Lab 3 : repondre uniquement a partir des passages, sinon une phrase de refus
exacte. Un bilan termine : reponses donnees, refus corrects.

## Ce qu'il faut faire remarquer

1. **Les trois premieres questions recoivent leur reponse**, et la procedure
   qui la contient figure parmi les passages. La premiere ne partage aucun mot
   avec la procedure sur le travail a distance : c'est le sens qui l'a trouvee.
2. **Les deux dernieres sont refusees.** La recherche renvoie pourtant des
   passages : elle renvoie toujours les plus proches, meme quand la reponse
   n'existe pas. C'est le modele, en les lisant, qui constate qu'elle n'y est
   pas. Ce refus est ce qui rend un RAG fiable : sans document, le meme modele
   repond « 4 jours » pour le mariage, de memoire.
3. **Les modes**, si le temps le permet. Par les mots seuls, la premiere
   question ne trouve aucun passage : pas un mot en commun. Par le sens seul,
   regarder a quel rang arrive l'astreinte sur PR-045 : un code n'a pas de
   sens pour un embedding. L'hybride cumule les deux, c'est le reglage qu'on
   met en production.

A verifier a la repetition : en mode hybride, le bilan doit etre de 3 sur 3
et 2 sur 2.

## Reglages

- Recherche lexicale : BM25 sur les racines des mots, sans les mots vides.
  « procedure » et « interne » en font partie : ils sont dans le titre de
  chaque procedure et ne distinguent rien. Un code comme PR-045 reste un seul
  mot. Seuls les passages qui partagent au moins un mot avec la question sont
  retenus.
- Fusion hybride : rang reciproque, poids egaux, c = 60, la valeur par defaut
  de LangChain (constantes `POIDS` et `C` en tete du script).

## Lien avec le Lab 3

Le Lab 3 reprend le meme corpus, le meme decoupage, le meme modele
d'embedding (`text-embedding-3-small`), la meme base Chroma et le meme prompt.
Les participants y construisent eux-memes ce que la demo montre :

- l'ecriture des trois recherches et du prompt (etapes 3 et 4, diapositives
  17 et 18) ;
- la mesure sur douze questions de reference, plutot qu'au ressenti ;
- la mise a jour d'une procedure et la reindexation (etape 5).

Deux differences, a connaitre si un participant compare : le Lab 3 part
d'autres reglages de fusion, que les participants font varier, et son
`decouper` garde les mots vides. BM25 y classe donc aussi sur « de » ou
« pour », ce qui explique une partie de ses echecs (Q6).
