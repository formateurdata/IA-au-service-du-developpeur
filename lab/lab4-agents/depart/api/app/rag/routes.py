"""La route de l'assistant, utilisée par la page « Assistant procédures »."""
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.rag.assistant import repondre

routeur = APIRouter()


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    mode: Literal["aucun", "semantique", "lexicale", "hybride"] = "hybride"


@routeur.post("/api/assistant")
def demander(corps: Question):
    try:
        return repondre(corps.question, corps.mode)
    except NotImplementedError as erreur:
        raise HTTPException(501, f"Pas encore écrit : {erreur}")
    except Exception:  # réseau, clé, quota : rien de technique à l'écran
        raise HTTPException(503, "L'assistant est indisponible pour le moment.")
