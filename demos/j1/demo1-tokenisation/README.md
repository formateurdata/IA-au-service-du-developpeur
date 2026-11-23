# Jour 1 - Demo 1 : observer la tokenisation

**Diapositive 10.** Le script tourne en local avec tiktoken, sans cle.
tiktoken est installe par `uv sync` a la racine de la formation. Lancer le
script la veille avec le reseau, une fois par encodage : les encodages restent
dans `cache-tiktoken/`, a cote du script.
`--offline` garantit ensuite qu'aucun acces reseau n'est tente.

```bash
uv run --offline tokenisation.py "Le modèle calcule, il ne comprend pas."
uv run --offline tokenisation.py "The model computes, it does not understand."
uv run --offline tokenisation.py "calculTotalHT_v2"
```

L'option `--enc o200k_base` montre l'encodage des modeles recents d'OpenAI
(par defaut : `cl100k_base`).

## Ce qu'il faut faire remarquer

1. **La phrase en francais.** Le decoupage ne suit pas les mots : certains
   mots courants font un seul token, d'autres se coupent en deux ou trois.
2. **La meme idee en anglais.** Moins de tokens : le vocabulaire de tokens est
   optimise pour la langue la plus presente dans le corpus d'entrainement.
3. **L'identifiant de code.** `calculTotalHT_v2` explose en morceaux.

La facture d'une API se compte en tokens : la langue et le nommage changent le
prix. On le retrouve au Jour 2, avec le bloc `usage` de la demo 1.
