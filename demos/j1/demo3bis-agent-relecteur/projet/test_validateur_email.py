from validateur_email import valider_email


def test_adresse_valide():
    assert valider_email("alice@example.fr") == {"valide": True, "raison": None}


def test_adresse_vide():
    assert valider_email("")["valide"] is False


def test_espaces():
    assert valider_email(" alice@example.fr")["valide"] is False


def test_sans_arobase():
    assert valider_email("alice.example.fr")["valide"] is False


def test_domaine_sans_point():
    assert valider_email("alice@example")["valide"] is False


def test_trop_longue():
    assert valider_email("a" * 300 + "@example.fr")["valide"] is False
