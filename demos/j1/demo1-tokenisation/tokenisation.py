"""Tokenisation d'une phrase passee en argument.

Usage :
    uv run tokenisation.py "La phrase a tokeniser"
    uv run tokenisation.py --enc o200k_base "La phrase a tokeniser"

Le jour J, sans reseau : uv run --offline tokenisation.py "..."
"""

import argparse
import os

# L'encodage telecharge au premier lancement est garde a cote du script, et
# non dans le dossier temporaire du systeme, que macOS vide regulierement.
os.environ.setdefault(
    "TIKTOKEN_CACHE_DIR",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache-tiktoken"),
)

import tiktoken  # noqa: E402


def main():
    p = argparse.ArgumentParser(description="Tokenise une phrase avec tiktoken.")
    p.add_argument("texte", nargs="+", help="la phrase a tokeniser")
    p.add_argument(
        "--enc",
        default="cl100k_base",
        help="encodage tiktoken (cl100k_base, o200k_base, ...)",
    )
    args = p.parse_args()

    texte = " ".join(args.texte)
    enc = tiktoken.get_encoding(args.enc)
    ids = enc.encode(texte)

    print("Texte      : %s" % texte)
    print("Encodage   : %s" % args.enc)
    print("Caracteres : %d" % len(texte))
    print("Tokens     : %d" % len(ids))
    print()
    print("  %-4s %-9s %s" % ("rang", "id", "morceau"))
    for rang, tid in enumerate(ids):
        print("  %-4d %-9d %r" % (rang, tid, enc.decode([tid])))
    print()
    print("  " + " | ".join(enc.decode([t]) for t in ids))


if __name__ == "__main__":
    main()
