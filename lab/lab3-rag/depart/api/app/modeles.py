"""Les données échangées par l'API."""
from typing import Literal

from pydantic import BaseModel, Field, model_validator

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


class ChangementStatut(BaseModel):
    """Le corps attendu par PATCH /api/demandes/{id}/statut."""

    statut: Literal["validee", "refusee", "livree"]
    motif_refus: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def motif_obligatoire_pour_un_refus(self) -> "ChangementStatut":
        if self.statut != "refusee":
            self.motif_refus = None
            return self
        motif = (self.motif_refus or "").strip()
        if not motif:
            raise ValueError("Un refus doit être motivé")
        self.motif_refus = motif
        return self
