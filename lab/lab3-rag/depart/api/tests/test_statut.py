"""Changer le statut d'une demande : PATCH /api/demandes/{id}/statut."""
import pytest

NOUVELLE = {
    "demandeur": "Alice Durand",
    "service": "Développement",
    "materiel": "Webcam",
    "motif": "Réunions d'équipe à distance.",
}


def creer(client) -> int:
    return client.post("/api/demandes", json=NOUVELLE).json()["id"]


def changer(client, id_demande, statut, motif=None):
    corps = {"statut": statut}
    if motif is not None:
        corps["motif_refus"] = motif
    return client.patch(f"/api/demandes/{id_demande}/statut", json=corps)


def test_valider_puis_livrer(client):
    id_demande = creer(client)
    assert changer(client, id_demande, "validee").json()["statut"] == "validee"
    reponse = changer(client, id_demande, "livree")
    assert reponse.status_code == 200
    assert client.get(f"/api/demandes/{id_demande}").json()["statut"] == "livree"


def test_refuser_avec_motif(client):
    id_demande = creer(client)
    reponse = changer(client, id_demande, "refusee", "  Budget épuisé  ")
    assert reponse.status_code == 200
    assert reponse.json()["motif_refus"] == "Budget épuisé"


@pytest.mark.parametrize("motif", [None, "", "   "])
def test_refus_sans_motif(client, motif):
    id_demande = creer(client)
    assert changer(client, id_demande, "refusee", motif).status_code == 422
    assert client.get(f"/api/demandes/{id_demande}").json()["statut"] == "en_attente"


@pytest.mark.parametrize("chemin, interdit", [
    ([], "livree"),
    (["validee"], "refusee"),
    (["validee", "livree"], "validee"),
])
def test_transitions_interdites(client, chemin, interdit):
    id_demande = creer(client)
    for statut in chemin:
        changer(client, id_demande, statut)
    assert changer(client, id_demande, interdit, "motif").status_code == 409


def test_demande_refusee_definitive(client):
    id_demande = creer(client)
    changer(client, id_demande, "refusee", "Doublon")
    for statut in ("validee", "livree"):
        assert changer(client, id_demande, statut).status_code == 409


def test_demande_inexistante(client):
    assert changer(client, 9999, "validee").status_code == 404


def test_statut_inconnu(client):
    assert changer(client, creer(client), "perdue").status_code == 422
