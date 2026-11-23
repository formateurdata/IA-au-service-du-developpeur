# Jour 2 - Demo 4 : prompt court contre prompt detaille

**Diapositive 25.**

```bash
uv run generer_image.py --live   # avant la session : produit les deux images
python3 generer_image.py         # le jour J : affiche les prompts, les tokens
                                 # et les images generees lors de la repetition
```

## Avant la session : verifier le modele

Le modele d'image change souvent : `dall-e-3` a ete retire de l'API en mai
2026, `gpt-image-1` en octobre 2026. Le script utilise
`gpt-image-2.6-sunburst`. La veille, verifier sur la page des retraits
d'OpenAI (https://developers.openai.com/api/docs/deprecations) qu'il est
toujours disponible, et changer `MODELE` en tete du script si besoin.

## Particularite de cette demo

C'est la seule dont le plan B n'est pas un rejeu de texte : ce sont les deux
fichiers PNG produits lors de la repetition, conserves dans `sorties/` avec
leurs compteurs de tokens (`sorties/infos.json`).

**Faire tourner cette demo la veille est donc obligatoire**, sinon il n'y a
rien a montrer en cas de coupure.

## Ce qu'il faut projeter

1. Les deux prompts cote a cote. Faire remarquer le rapport de longueur avant
   meme de montrer les images.
2. Les deux images cote a cote.
3. Demander au groupe quels elements du prompt detaille se retrouvent
   visiblement dans la seconde image.

## Le point technique : une image se facture en tokens

Le script affiche le bloc `usage` de chaque generation. Comparer les tokens
d'entree des deux prompts, puis les tokens de sortie, qui correspondent a
l'image produite. C'est le meme compteur que pour le texte (demo 1) : le
prompt detaille coute un peu plus en entree, l'essentiel de la facture est
ailleurs.

Si le service renvoie un prompt reecrit, le script l'affiche aussi : le prompt
execute n'est alors pas celui qu'on a ecrit.

## La chute

Meme principe qu'au Jour 1 sur le code, et qu'a l'etape 2 du Lab 2 : la
contrainte n'appauvrit pas le resultat, elle le rend reproductible.
