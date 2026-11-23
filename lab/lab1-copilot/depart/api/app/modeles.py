"""Les données échangées par l'API."""
from typing import Literal

from pydantic import BaseModel, Field

Statut = Literal["en_attente", "validee", "refusee", "livree"]


class NouvelleDemande(BaseModel):
    """Le corps attendu par POST /api/demandes."""

    demandeur: str = Field(min_length=2, max_length=80)
    service: str = Field(min_length=2, max_length=80)
    materiel: str = Field(min_length=2, max_length=80)
    motif: str = Field(min_length=5, max_length=500)


class Demande(NouvelleDemande):
    """Une demande telle qu'elle est stockée et renvoyée."""

    id: int
    statut: Statut
    motif_refus: str | None = None
    date_creation: str
