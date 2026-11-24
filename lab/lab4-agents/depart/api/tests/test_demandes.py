NOUVELLE = {
    "demandeur": "Alice Durand",
    "service": "Développement",
    "materiel": "Webcam",
    "motif": "Réunions d'équipe à distance.",
}


def test_liste_complete(client):
    reponse = client.get("/api/demandes")
    assert reponse.status_code == 200
    assert len(reponse.json()) == 30


def test_filtre_par_statut(client):
    demandes = client.get("/api/demandes", params={"statut": "validee"}).json()
    assert demandes
    assert all(d["statut"] == "validee" for d in demandes)


def test_recherche_dans_le_materiel(client):
    demandes = client.get("/api/demandes", params={"q": "casque"}).json()
    assert len(demandes) == 3
    assert all("casque" in d["materiel"].lower() for d in demandes)


def test_recherche_dans_le_demandeur(client):
    demandes = client.get("/api/demandes", params={"q": "Benali"}).json()
    assert [d["demandeur"] for d in demandes] == ["Karim Benali"]


def test_lecture(client):
    demande = client.get("/api/demandes/1").json()
    assert demande["demandeur"] == "Camille Martin"


def test_creation(client):
    reponse = client.post("/api/demandes", json=NOUVELLE)
    assert reponse.status_code == 201
    creee = reponse.json()
    assert creee["statut"] == "en_attente"
    assert client.get(f"/api/demandes/{creee['id']}").json()["demandeur"] == "Alice Durand"


def test_creation_motif_trop_court(client):
    reponse = client.post("/api/demandes", json={**NOUVELLE, "motif": "?"})
    assert reponse.status_code == 422
