# Portail interne : demandes de matériel

L'application interne de l'entreprise pour demander du matériel informatique :
écran, portable, casque. Chaque demande est créée « en attente », puis traitée
par le responsable du parc.

## Lancer

```bash
uv run lancer.py
```

- Portail : http://localhost:5173
- API et sa documentation interactive : http://localhost:8000/docs

Au premier lancement, `uv` installe l'environnement Python de l'API et `npm`
celui de l'interface. La base SQLite `api/portail.db` est créée et remplie
avec trente demandes. Pour repartir de zéro, supprimer ce fichier.

## Structure

| Dossier | Contenu | Tests |
|---|---|---|
| `api/` | FastAPI, SQLite (module `sqlite3`), Pydantic | `cd api && uv run pytest` |
| `web/` | React 19, Vite, TypeScript | `cd web && npm test` |

## L'API

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/demandes?q=&statut=` | Liste, les plus récentes d'abord. `q` cherche dans le demandeur et le matériel |
| GET | `/api/demandes/{id}` | Une demande |
| POST | `/api/demandes` | Crée une demande, statut `en_attente` |
| PATCH | `/api/demandes/{id}/statut` | Valide, refuse (avec motif) ou marque livrée une demande |
| POST | `/api/cartes` | Génère une carte de bienvenue (HTML et CSS) avec un modèle |

Statuts : `en_attente`, `validee`, `refusee`, `livree`.
