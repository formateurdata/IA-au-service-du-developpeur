# Jour 2 - Demo 2 : prompt template et chaine

**Diapositive 10.**

```bash
uv run template_chain.py --live --enregistrer   # avant la session
python3 template_chain.py                       # le jour J
```

## Le dispositif

Le gabarit produit le message d'accueil d'une carte de bienvenue : le sujet
du Lab 2, qui suit cette partie. Trois appels sur le meme gabarit :

- appels 1 et 2 : meme personne, **ton different**
- appels 1 et 3 : meme ton, **personne differente**

Le script affiche pour chaque appel le prompt reellement envoye, ce qui rend
visible la substitution des variables.

## Le message

Aucun prompt n'a ete reecrit a la main. Sans template, ces trois prompts
seraient trois chaines de caracteres codees en dur dans l'application.

La formule a garder : **un prompt en dur est une dette technique au meme
titre qu'une requete SQL en dur.**

## Lien avec les labs

- **Lab 2.** Meme principe, sans LangChain : les regles de format sont ecrites
  une seule fois dans le prompt systeme (`SYSTEME`), et seule la description
  de l'utilisateur change d'un appel a l'autre.
- **Lab 3.** LangChain y sert vraiment : base vectorielle Chroma, embeddings
  et modele de conversation derriere une meme interface.

## Si un participant demande si LangChain est obligatoire

Repondre non, et c'est important pour la credibilite du propos. Pour un appel
simple, appeler l'API directement est plus lisible et plus facile a deboguer :
c'est le choix du Lab 2. L'orchestrateur se justifie des qu'il y a memoire,
recuperation documentaire ou enchainement d'appels : c'est le cas de la demo 3
et du Lab 3.
