"""Jour 2 - Demo 4 : prompt court contre prompt detaille

Meme idee, deux prompts. Les images restent dans sorties/ et constituent le
plan B : cette demo est la seule qui ne peut pas etre rejouee sans elles,
donc la lancer une fois avant la session est obligatoire. Voir README.md.
"""
import base64
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import commun  # noqa: E402

SORTIES = os.path.join(os.path.dirname(__file__), "sorties")
INFOS = os.path.join(SORTIES, "infos.json")
# dall-e-3 est retire de l'API depuis mai 2026, gpt-image-1 depuis octobre 2026.
# Verifier la veille sur https://developers.openai.com/api/docs/deprecations
MODELE = "gpt-image-2.6-sunburst"
PROMPTS = [
    ("1-prompt-court.png", "Un poste de travail de developpeur."),
    ("2-prompt-detaille.png",
     "Un poste de travail de developpeur photographie de trois quarts, "
     "lumiere naturelle rasante de fin de journee venant d'une fenetre a "
     "gauche, palette sobre en bois clair et gris ardoise, un seul ecran "
     "allume affichant du code, bureau range, faible profondeur de champ, "
     "style photographie editoriale, format paysage."),
]


def collecte():
    from openai import OpenAI
    client = OpenAI(api_key=commun.cle())
    os.makedirs(SORTIES, exist_ok=True)
    infos = {}
    for nom, prompt in PROMPTS:
        r = client.images.generate(model=MODELE, prompt=prompt, n=1,
                                   size="1536x1024")
        image = r.data[0] if r.data else None
        if image is None or not image.b64_json:
            sys.exit("Le service n'a renvoye aucune image pour %s." % nom)
        open(os.path.join(SORTIES, nom), "wb").write(base64.b64decode(image.b64_json))
        infos[nom] = {
            "usage": r.usage.model_dump(mode="json") if r.usage else None,
            "prompt_reecrit": image.revised_prompt,
        }
    # Garde les compteurs avec les images, pour les montrer aussi en rejeu.
    json.dump(infos, open(INFOS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return infos


def montre(infos):
    for nom, prompt in PROMPTS:
        commun.bloc("%s (%d caracteres)" % (nom, len(prompt)))
        print("  " + prompt)
        info = infos.get(nom) or {}
        usage = info.get("usage")
        if usage:
            print("  tokens : entree %s, sortie %s (l'image produite)"
                  % (usage.get("input_tokens"), usage.get("output_tokens")))
        if info.get("prompt_reecrit"):
            print("  prompt reecrit par le service :\n  " + info["prompt_reecrit"])


if __name__ == "__main__":
    # Plan B specifique : des fichiers PNG, pas un rejeu JSON.
    if "--live" in sys.argv:
        commun.lancer(__doc__, os.devnull, collecte, montre, deps=("openai",))
        print("\nImages dans %s" % SORTIES)
    else:
        images = sorted(f for f in os.listdir(SORTIES)
                        if f.endswith(".png")) if os.path.isdir(SORTIES) else []
        infos = json.load(open(INFOS, encoding="utf-8")) if os.path.exists(INFOS) else {}
        montre(infos)
        commun.bloc("Plan B")
        print("  " + ("\n  ".join(images) if images else
                      "Aucune image. Lancer avant la session :\n  "
                      + commun.cmd(" --live")))
