"""API de démonstration : la liste des demandes de matériel du portail."""
from fastapi import FastAPI

from app.modeles import Demande

app = FastAPI(title="Portail interne")

DEMANDES = [
    Demande(id=1, demandeur="Camille Martin", materiel="Écran 27 pouces", statut="en_attente"),
    Demande(id=2, demandeur="Karim Benali", materiel="Casque audio", statut="livree"),
    Demande(id=3, demandeur="Jeanne D'Almeida", materiel="Ordinateur portable",
            statut="en_attente"),
]


@app.get("/api/demandes", response_model=list[Demande])
def lister():
    """Liste les demandes dans l'ordre du portail."""
    return DEMANDES
