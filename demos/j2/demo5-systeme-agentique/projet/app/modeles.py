"""Les données échangées par l'API, reprises du portail des labs."""
from typing import Literal

from pydantic import BaseModel

Statut = Literal["en_attente", "validee", "refusee", "livree"]


class Demande(BaseModel):
    """Une demande de matériel telle que l'API la renvoie."""

    id: int
    demandeur: str
    materiel: str
    statut: Statut
