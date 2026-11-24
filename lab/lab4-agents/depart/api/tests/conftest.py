import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Un client de test sur une base neuve, remplie avec les demandes initiales."""
    monkeypatch.setattr(db, "CHEMIN", tmp_path / "test.db")
    with TestClient(app) as c:
        yield c
