# AGENTS.md

Règles du projet pour les assistants de code. Exemple de référence du lab 1 :
le vôtre doit venir de ce que vous avez observé à l'étape 1.

## Projet

Portail interne de demandes de matériel. `api/` : FastAPI, SQLite par le
module `sqlite3`, Pydantic. `web/` : React 19, Vite, TypeScript strict.

## Commandes

- Tout lancer : `uv run lancer.py`
- Tests API : `cd api && uv run pytest`
- Tests interface : `cd web && npm test`, puis `npm run typecheck`

## Conventions

- Nommage en français, comme le code existant.
- API : toute valeur venant de l'utilisateur passe en paramètre `?` de la
  requête SQL, jamais par f-string ni concaténation.
- API : le corps des requêtes est validé par un modèle Pydantic ; pas de
  vérification à la main dans la route.
- API : codes de statut explicites. 404 si la ressource est absente, 409 si
  l'état actuel interdit l'opération, 422 si le corps est invalide.
- API : un message d'erreur n'expose ni requête SQL, ni trace, ni chemin.
- Interface : composants fonctionnels, un composant par fichier.
- Interface : toute liste rendue a pour clé l'identifiant de l'élément,
  jamais l'index.
- Interface : tout appel à `fetch` vérifie `response.ok` avant de lire le corps.
- Interface : un effet qui lance une requête l'annule dans sa fonction de
  nettoyage (`AbortController`).

## Interdits

- Aucune nouvelle dépendance, ni Python ni npm : pas d'axios, de lodash, de
  react-query, d'ORM.
- Pas de `any` en TypeScript. Pas de `dangerouslySetInnerHTML`.
- Ne pas modifier les tests existants pour les faire passer.

## Définition de terminé

1. Les critères d'acceptation du ticket sont tous couverts par un test.
2. `uv run pytest` et `npm test` passent, `npm run typecheck` ne signale rien.
3. Les cas limites sont testés : ressource absente, corps invalide, liste
   vide, erreur réseau.
4. Avant d'annoncer la fin, lancer les commandes ci-dessus et montrer leur
   résultat.
