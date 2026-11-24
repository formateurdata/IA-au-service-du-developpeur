"""Accès à la base SQLite du portail."""
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from app.donnees import DEMANDES_INITIALES

CHEMIN = Path(os.environ.get("PORTAIL_BASE",
                             Path(__file__).resolve().parent.parent / "portail.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS demandes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    demandeur TEXT NOT NULL,
    service TEXT NOT NULL,
    materiel TEXT NOT NULL,
    motif TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'en_attente',
    motif_refus TEXT,
    date_creation TEXT NOT NULL
)
"""


def connexion() -> sqlite3.Connection:
    con = sqlite3.connect(CHEMIN, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def base():
    """Dépendance FastAPI : une connexion par requête, fermée à la fin."""
    con = connexion()
    try:
        yield con
    finally:
        con.close()


def date_iso(date_francaise: str) -> str:
    """JJ/MM/AAAA vers AAAA-MM-JJ : la seule forme qui se trie comme du texte."""
    return datetime.strptime(date_francaise, "%d/%m/%Y").date().isoformat()


def initialiser() -> None:
    """Crée la table et la remplit au premier lancement.

    Les dates sont stockées au format ISO. Une base créée avant cette
    correction garde ses dates JJ/MM/AAAA : supprimer api/portail.db.
    """
    with closing(connexion()) as con:
        con.execute(SCHEMA)
        if con.execute("SELECT COUNT(*) FROM demandes").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO demandes (demandeur, service, materiel, motif, statut,"
                " motif_refus, date_creation) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(*ligne[:6], date_iso(ligne[6])) for ligne in DEMANDES_INITIALES])
        con.commit()
