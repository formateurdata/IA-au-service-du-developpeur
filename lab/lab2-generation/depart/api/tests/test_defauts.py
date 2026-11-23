"""Les défauts présents dans l'application de départ, prouvés puis corrigés.

Chaque test échoue sur l'application de départ et passe une fois le défaut corrigé.
"""


def test_recherche_avec_apostrophe(client):
    """D1 : la recherche concaténait le texte saisi dans la requête SQL."""
    reponse = client.get("/api/demandes", params={"q": "D'Almeida"})
    assert reponse.status_code == 200
    assert [d["demandeur"] for d in reponse.json()] == ["Jeanne D'Almeida"]


def test_recherche_ne_contourne_pas_le_filtre(client):
    """D1 : une saisie piégée ne doit pas élargir les résultats."""
    reponse = client.get("/api/demandes", params={"q": "zzz' OR '1'='1"})
    assert reponse.status_code == 200
    assert reponse.json() == []


def test_demande_inexistante_404(client):
    """D2 : une demande absente provoquait une erreur 500."""
    assert client.get("/api/demandes/9999").status_code == 404


def test_tri_par_date_decroissante(client):
    """D3 : les dates JJ/MM/AAAA étaient triées comme du texte."""
    dates = [d["date_creation"] for d in client.get("/api/demandes").json()]
    assert dates == sorted(dates, reverse=True)
    assert dates[0] == "2026-11-21"
