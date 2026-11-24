"""Jour 2 · Démo 6 · Lire un texte à voix haute avec OpenAI."""

import argparse
import base64
import sys
import wave
from datetime import datetime
from itertools import count
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import commun

# Modifiez ces champs avant de lancer la démo avec --live.
TEXTE = """Bonjour et bienvenue au deuxième jour de la formation."""

LANGUE = ""  # Exemples : "anglais", "espagnol". Vide = langue du texte.
PERSONA = "animatrice radio enthousiaste"
VOIX = "cedar"

MODELE = "gpt-realtime-2.1-mini"
FREQUENCE = 24000
SORTIE = Path(__file__).resolve().parent / "sortie"

# USD par million de tokens pour gpt-realtime-2.1-mini, au 24 novembre 2026.
# https://developers.openai.com/api/docs/models/gpt-realtime-2.1-mini
PRIX_ENTREE_TEXTE = 0.60
PRIX_ENTREE_CACHE = 0.06
PRIX_SORTIE_TEXTE = 2.40
PRIX_SORTIE_AUDIO = 20.00


def afficher_cout(usage):
    if not usage or not usage.input_token_details or not usage.output_token_details:
        print("Coût estimé indisponible (détail des tokens absent).")
        return

    # Cette démo envoie uniquement du texte et reçoit du texte et de l’audio.
    entree = usage.input_tokens
    cache = usage.input_token_details.cached_tokens
    sortie = usage.output_tokens
    audio = usage.output_token_details.audio_tokens
    if None in (entree, cache, sortie, audio):
        print("Coût estimé indisponible (compteurs de tokens incomplets).")
        return

    texte = sortie - audio
    cout_entree = (
        (entree - cache) * PRIX_ENTREE_TEXTE + cache * PRIX_ENTREE_CACHE
    ) / 1_000_000
    cout_sortie = (texte * PRIX_SORTIE_TEXTE + audio * PRIX_SORTIE_AUDIO) / 1_000_000
    print(
        f"Entrée (IN)  : {entree} tokens texte, dont {cache} en cache → {cout_entree:.8f} USD"
    )
    print(
        f"Sortie (OUT) : {texte} tokens texte et {audio} tokens audio → {cout_sortie:.8f} USD"
    )
    print(f"Total estimé : {cout_entree + cout_sortie:.8f} USD")


def synthetiser(texte, cle, langue, persona):
    from openai import OpenAI

    instructions = ["Lis uniquement le texte fourni, sans introduction ni commentaire."]
    if langue.strip():
        instructions.append(
            f"Langue de lecture : {langue.strip()}. "
            "Si le texte est dans une autre langue, traduis-le fidèlement avant de le lire. "
            "Sinon, conserve ses mots."
        )
    else:
        instructions.append("Conserve les mots et la langue du texte.")
    if persona.strip():
        instructions.append(
            f"Adopte ce style de narration pour le ton et le rythme : {persona.strip()}."
        )
    else:
        instructions.append("Lis sur un ton neutre.")

    audio = bytearray()
    with OpenAI(api_key=cle).realtime.connect(model=MODELE) as session:
        session.response.create(
            response={
                "instructions": " ".join(instructions),
                "input": [
                    {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": texte}],
                    }
                ],
                "output_modalities": ["audio"],
                "audio": {
                    "output": {
                        "voice": VOIX,
                        "format": {"type": "audio/pcm", "rate": FREQUENCE},
                    }
                },
            }
        )
        for evenement in session:
            if evenement.type == "response.output_audio.delta":
                audio.extend(base64.b64decode(evenement.delta))
            elif evenement.type == "error":
                sys.exit(
                    f"OpenAI a refusé la lecture ({evenement.error.code or evenement.error.type})."
                )
            elif evenement.type == "response.done":
                afficher_cout(evenement.response.usage)
                if evenement.response.status == "completed" and audio:
                    return audio
                sys.exit(f"Lecture incomplète (statut {evenement.response.status}).")
    sys.exit("Connexion fermée avant la fin de la lecture.")


def enregistrer(audio):
    SORTIE.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=SORTIE) as dossier:
        temporaire = Path(dossier) / "lecture.wav"
        with wave.open(str(temporaire), "wb") as fichier:
            fichier.setnchannels(1)
            fichier.setsampwidth(2)
            fichier.setframerate(FREQUENCE)
            fichier.writeframes(audio)

        date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        for numero in count(1):
            suffixe = "" if numero == 1 else f"_{numero}"
            chemin = SORTIE / f"lecture-{date}{suffixe}.wav"
            try:
                chemin.hardlink_to(temporaire)
            except FileExistsError:
                continue
            return chemin


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="générer un nouveau fichier WAV"
    )
    parser.add_argument("--texte", help="phrase à lire en mode direct")
    args = parser.parse_args()

    if args.texte is not None and not args.live:
        parser.error("--texte nécessite --live.")
    if args.live:
        texte = (TEXTE if args.texte is None else args.texte).strip()
        if not texte:
            parser.error(
                "Renseignez le champ TEXTE ou utilisez --texte avec une phrase à lire."
            )
        cle = commun.cle()
        if not cle:
            sys.exit(
                "Renseignez OPENAI_API_KEY dans demos/.env ou dans l’environnement."
            )
        from websockets.exceptions import WebSocketException

        try:
            audio = synthetiser(texte, cle, LANGUE, PERSONA)
        except (OSError, WebSocketException) as erreur:
            if "invalid_api_key" in str(erreur):
                sys.exit("OpenAI a refusé la clé. Vérifiez OPENAI_API_KEY.")
            sys.exit(
                "Connexion à OpenAI interrompue. Vérifiez le réseau et l’accès à Realtime."
            )
        chemin = enregistrer(audio)
    else:
        fichiers = (p for p in SORTIE.glob("lecture*.wav") if p.is_file())
        chemin = max(fichiers, key=lambda p: p.stat().st_mtime_ns, default=None)
        if chemin is None:
            sys.exit("Aucun enregistrement. Lancez d’abord la démo avec --live.")
    print(f"Voix générée par IA. Fichier à écouter : {chemin}")


if __name__ == "__main__":
    main()
