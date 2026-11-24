# Jour 2 · Démo 6 · Du texte à la voix

Ouvrez [synthese_vocale.py](synthese_vocale.py) et modifiez les champs en tête du fichier.

| Champ | Exemple | Effet |
|---|---|---|
| `TEXTE` | `"""Le train pour Lyon partira dans cinq minutes."""` | Texte à lire, sur une ou plusieurs lignes. |
| `LANGUE` | `"anglais"` | Demande une lecture en anglais, avec traduction si nécessaire. Laissez `""` pour garder la langue du texte. |
| `PERSONA` | `"cheffe de gare calme et rassurante"` | Guide le ton et le rythme de la voix. Laissez `""` pour une lecture neutre. |
| `VOIX` | `"marin"` | Choisit la voix de synthèse. La valeur par défaut est `"cedar"`. |

Vous pouvez renseigner la langue et le persona indépendamment. Pour comparer deux lectures en salle, gardez le même texte et changez seulement le persona.

## Changer de voix

Pour essayer la voix `marin`, modifiez la variable `VOIX` en tête de `synthese_vocale.py`.

```python
VOIX = "marin"
```

Les dix voix intégrées de l’API Realtime sont `alloy`, `ash`, `ballad`, `cedar`, `coral`, `echo`, `marin`, `sage`, `shimmer` et `verse`. Utilisez le nom en minuscules. [Voix disponibles dans l’API Realtime](https://developers.openai.com/api/docs/guides/realtime-conversations#voice-options)

Pour entendre la différence de timbre, gardez les mêmes valeurs de `TEXTE`, `LANGUE` et `PERSONA`, puis relancez `uv run synthese_vocale.py --live` depuis le dossier de la démo. Vous pourrez comparer les deux WAV dans `sortie/`.

## Lancer la démo

À la racine de la formation, lancez `uv sync`. Le script utilise la clé `OPENAI_API_KEY` de l’environnement ou celle du fichier `demos/.env`, comme les autres démos.

```bash
cd demos/j2/demo6-text-to-speech
uv run synthese_vocale.py --live
```

À la fin de l’appel, le script affiche les tokens d’entrée (dont ceux en cache), les tokens de sortie (texte et audio) et le coût estimé de chaque côté, puis le total en USD. Le calcul utilise les compteurs renvoyés par OpenAI et les tarifs du modèle au 24 novembre 2026. [Tarifs de GPT-Realtime-2.1 mini](https://developers.openai.com/api/docs/models/gpt-realtime-2.1-mini)

Ouvrez le fichier WAV indiqué par le script dans votre lecteur audio. Pour faire entendre l’effet de la ponctuation, demandez au groupe de placer les pauses, puis essayez sa version du texte.

```bash
uv run synthese_vocale.py --live --texte "On déploie ? Maintenant ? Très bien, allons-y !"
```

Chaque génération ajoute dans `sortie/` un fichier daté, par exemple `lecture-2026-11-24_14-30-05.wav`. Si deux lectures sont générées la même seconde, la suivante reçoit le suffixe `_2`. Pour comparer plusieurs prises hors ligne, ouvrez leurs fichiers. La commande `python3 synthese_vocale.py` affiche le chemin de la prise la plus récente.

Dans [le script](synthese_vocale.py), `input` contient le texte à lire et `instructions` indique comment le prononcer. L’API Realtime renvoie le son par fragments. Le script les assemble puis écrit un WAV mono à 24 kHz. [Documentation OpenAI](https://developers.openai.com/api/docs/guides/realtime-conversations)
