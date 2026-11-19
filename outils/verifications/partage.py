"""Refuse ce qui ne doit pas partir dans un dépôt partagé.

- chemins absolus vers un dossier personnel (/Users/<nom>/, /home/<nom>/, C:\\Users\\<nom>\\) ;
- URL d'Artifact claude.ai, liées au compte qui les a publiées.

Les gros fichiers sont refusés par le hook check-added-large-files.
Code de sortie 1 si quelque chose est trouvé.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MOTIFS = {
    "chemin absolu personnel": re.compile(
        r"(?<![\w.])(?:/Users/|/home/|[A-Za-z]:\\Users\\)(?!<|\{|\$|\*|nom\b|user\b|vous\b)[A-Za-z0-9._-]+"
    ),
    "URL d'Artifact liée à un compte": re.compile(r"claude\.ai/(?:code/)?artifact/[A-Za-z0-9-]{8,}"),
}


def controler_texte(texte: str) -> list[str]:
    problemes = []
    for n, ligne in enumerate(texte.splitlines(), start=1):
        for libelle, motif in MOTIFS.items():
            for m in motif.finditer(ligne):
                problemes.append(f"ligne {n} : {libelle} « {m.group(0)} »")
    return problemes


def controler_fichier(chemin: Path) -> list[str]:
    donnees = chemin.read_bytes()
    if b"\0" in donnees[:8192]:
        return []  # fichier binaire
    return [f"{chemin} {p}" for p in controler_texte(donnees.decode("utf-8", errors="replace"))]


def main(arguments: list[str]) -> int:
    problemes = [p for a in arguments for p in controler_fichier(Path(a))]
    for p in problemes:
        print(f"✖ Partage : {p}", file=sys.stderr)
    return 1 if problemes else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
