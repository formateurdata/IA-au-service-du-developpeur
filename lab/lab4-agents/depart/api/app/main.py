"""API du portail interne : demandes de matériel informatique.

    uv run uvicorn app.main:app --reload --port 8000
    Documentation interactive : http://localhost:8000/docs
"""
import asyncio
import os
import random
import sqlite3
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app import db
from app.modeles import ChangementStatut, Demande, NouvelleDemande, Statut
from app.rag.routes import routeur as routeur_assistant

RESEAU_INSTABLE = os.environ.get("PORTAIL_RESEAU_INSTABLE") == "1"

# Les seuls changements de statut autorisés. Tout le reste est refusé (409).
TRANSITIONS: dict[str, set[str]] = {
    "en_attente": {"validee", "refusee"},
    "validee": {"livree"},
}


@asynccontextmanager
async def cycle_de_vie(_app: FastAPI):
    db.initialiser()
    yield


app = FastAPI(title="Portail interne", lifespan=cycle_de_vie)
app.include_router(routeur_assistant)


@app.middleware("http")
async def reseau_instable(request: Request, appel_suivant):
    """En mode instable, la liste répond lentement et échoue parfois, comme en production."""
    if RESEAU_INSTABLE and request.method == "GET" and request.url.path == "/api/demandes":
        await asyncio.sleep(random.uniform(0.15, 0.9))
        if random.random() < 1 / 8:
            return JSONResponse({"detail": "Service momentanément indisponible"},
                                status_code=503)
    return await appel_suivant(request)


@app.get("/api/demandes", response_model=list[Demande])
def lister(q: str | None = None, statut: Statut | None = None,
           con: sqlite3.Connection = Depends(db.base)):
    """Liste les demandes, les plus récentes d'abord. q cherche dans le demandeur et le matériel."""
    requete = "SELECT * FROM demandes"
    conditions, parametres = [], []
    if q:
        # Le texte saisi est un paramètre, jamais un morceau de la requête.
        conditions.append("(demandeur LIKE ? OR materiel LIKE ?)")
        parametres += [f"%{q}%", f"%{q}%"]
    if statut:
        conditions.append("statut = ?")
        parametres.append(statut)
    if conditions:
        requete += " WHERE " + " AND ".join(conditions)
    requete += " ORDER BY date_creation DESC, id DESC"
    return [Demande(**ligne) for ligne in con.execute(requete, parametres)]


@app.get("/api/demandes/{id_demande}", response_model=Demande)
def lire(id_demande: int, con: sqlite3.Connection = Depends(db.base)):
    ligne = con.execute("SELECT * FROM demandes WHERE id = ?", (id_demande,)).fetchone()
    if ligne is None:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    return Demande(**ligne)


@app.post("/api/demandes", response_model=Demande, status_code=201)
def creer(demande: NouvelleDemande, con: sqlite3.Connection = Depends(db.base)):
    curseur = con.execute(
        "INSERT INTO demandes (demandeur, service, materiel, motif, statut, date_creation)"
        " VALUES (?, ?, ?, ?, 'en_attente', ?)",
        (demande.demandeur, demande.service, demande.materiel, demande.motif,
         date.today().isoformat()))
    con.commit()
    return lire(curseur.lastrowid, con)


@app.patch("/api/demandes/{id_demande}/statut", response_model=Demande)
def changer_statut(id_demande: int, changement: ChangementStatut,
                   con: sqlite3.Connection = Depends(db.base)):
    """Valide, refuse ou livre une demande, selon TRANSITIONS."""
    actuelle = lire(id_demande, con)
    if changement.statut not in TRANSITIONS.get(actuelle.statut, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Transition interdite : {actuelle.statut} vers {changement.statut}")
    # La condition sur l'ancien statut évite qu'un changement concurrent soit écrasé.
    curseur = con.execute(
        "UPDATE demandes SET statut = ?, motif_refus = ? WHERE id = ? AND statut = ?",
        (changement.statut, changement.motif_refus, id_demande, actuelle.statut))
    con.commit()
    if curseur.rowcount == 0:
        raise HTTPException(status_code=409, detail="La demande a changé entre-temps")
    return lire(id_demande, con)
