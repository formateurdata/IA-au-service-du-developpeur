# Jour 2 - Demo 1 : premier appel a l'API

**Diapositive 7.** Meme API que le Lab 2 : `client.responses.create`.

```bash
uv run appel_brut.py --live --enregistrer   # avant la session (API OpenAI)
python3 appel_brut.py                       # le jour J : rejeu de la sortie figee
```

## Ce qu'il faut projeter, dans l'ordre

1. **La requete.** Trois elements suffisent : le modele, les instructions (le
   role systeme) et la demande de l'utilisateur. Faire constater qu'il n'y a
   rien d'autre. C'est exactement l'appel que les stagiaires ecriront a
   l'etape 1 du Lab 2.
2. **La reponse brute, en JSON.** Ne pas la mettre en forme : l'objectif est
   de demystifier. Un appel a un LLM est une requete HTTP comme une autre.
3. **Le bloc `usage`.** C'est le compteur de tokens du Jour 1, en vrai :
   `input_tokens` et `output_tokens`, factures a des prix differents. Le
   script affiche le cout de l'appel et celui de 1 000 appels, avec les memes
   prix que le Lab 2 (`app/config.py`).
4. **`status`.** Le script refait le meme appel avec `max_output_tokens=16`.
   `completed` signifie que le modele a termine ; `incomplete`, avec la raison
   `max_output_tokens`, signifie que la reponse a ete coupee. C'est le champ
   que personne ne regarde et qui explique les reponses tronquees en
   production.

## La chute

Tout ce qui suit dans la journee s'ajoute autour de cet appel, sans le
remplacer : le format impose (diapositive 8 et etape 2 du Lab 2), les delais
et les erreurs (etape 4B), puis LangChain qui orchestre ce meme appel.
