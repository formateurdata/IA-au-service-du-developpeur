from fastapi.testclient import TestClient

from app.main import app


def test_liste_dans_l_ordre_du_portail():
    reponse = TestClient(app).get("/api/demandes")

    assert reponse.status_code == 200
    assert [demande["id"] for demande in reponse.json()] == [1, 2, 3]
