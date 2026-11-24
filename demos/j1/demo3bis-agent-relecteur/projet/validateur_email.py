"""Validation d'une adresse e-mail plausible.

valider_email(valeur) retourne {"valide": bool, "raison": str | None} :
raison vaut None pour une adresse valide, une explication sinon.

Une adresse est refusée si elle est vide, si elle commence ou finit par un
espace, si elle dépasse 254 caractères, si elle n'a pas exactement un
arobase, ou si son domaine n'a pas de point.
"""

LONGUEUR_MAX = 254


def valider_email(valeur: str) -> dict:
    """Retourne {"valide": bool, "raison": str | None}."""
    if valeur == "":
        return {"valide": False, "raison": "adresse vide"}
    if valeur != valeur.strip():
        return {"valide": False, "raison": "espace en début ou en fin"}
    if len(valeur) > LONGUEUR_MAX:
        return {"valide": False, "raison": "plus de 254 caractères"}
    if valeur.count("@") != 1:
        return {"valide": False, "raison": "il faut exactement un arobase"}
    domaine = valeur.split("@")[1]
    if "." not in domaine:
        return {"valide": False, "raison": "domaine sans point"}
    return {"valide": True, "raison": None}
