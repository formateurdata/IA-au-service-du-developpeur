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

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app import db
from app.modeles import Demande, NouvelleDemande, Statut

RESEAU_INSTABLE = os.environ.get("PORTAIL_RESEAU_INSTABLE") == "1"


@asynccontextmanager
async def cycle_de_vie(_app: FastAPI):
    db.initialiser()
    yield


app = FastAPI(title="Portail interne", lifespan=cycle_de_vie)


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
        conditions.append(f"(demandeur LIKE '%{q}%' OR materiel LIKE '%{q}%')")
    if statut:
        conditions.append("statut = ?")
        parametres.append(statut)
    if conditions:
        requete += " WHERE " + " AND ".join(conditions)
    requete += " ORDER BY date_creation DESC"
    return [Demande(**ligne) for ligne in con.execute(requete, parametres)]


@app.get("/api/demandes/{id_demande}", response_model=Demande)
def lire(id_demande: int, con: sqlite3.Connection = Depends(db.base)):
    ligne = con.execute("SELECT * FROM demandes WHERE id = ?", (id_demande,)).fetchone()
    return Demande(**ligne)


@app.post("/api/demandes", response_model=Demande, status_code=201)
def creer(demande: NouvelleDemande, con: sqlite3.Connection = Depends(db.base)):
    curseur = con.execute(
        "INSERT INTO demandes (demandeur, service, materiel, motif, statut, date_creation)"
        " VALUES (?, ?, ?, ?, 'en_attente', ?)",
        (demande.demandeur, demande.service, demande.materiel, demande.motif,
         date.today().strftime("%d/%m/%Y")))
    con.commit()
    return lire(curseur.lastrowid, con)
