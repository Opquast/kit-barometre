#!/usr/bin/env python3
"""Vérifie, avant chaque commit et chaque publication, qu'aucune donnée personnelle n'est sortie du dernier passage.

Cible : les dossiers du dernier passage (resultats/<outil>-AAAA-MM-JJ à la date la plus récente présente, quel que
soit le jour où on lance la vérification, par exemple le matin après un passage de nuit commencé la veille) et la
page suivi-barometre.html. Cherche les adresses e-mail (hors adresses d'exemple, images @2x et règles @media) et les
numéros de téléphone français.

Codes de sortie : 0 rien trouvé ; 1 donnée personnelle trouvée ; 2 aucun fichier à vérifier (échec explicite, pour
qu'une vérification qui n'a rien lu ne passe jamais pour une vérification réussie).

Usage : python3 scripts/verifier_publication.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DATE_PASSAGE = re.compile(r"-(\d{4}-\d{2}-\d{2})$")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}")
TELEPHONE = re.compile(r"(?:\+33 ?|\b0)[1-9](?:[ .-]?\d{2}){4}\b")
AUTORISES = re.compile(r"exemple\.|example\.|@2x|@media")
EXTENSIONS = {".json", ".csv", ".tsv", ".md", ".html", ".txt", ".har"}
CODE_TROUVE, CODE_RIEN_A_VERIFIER = 1, 2


def dossiers_du_dernier_passage(resultats: Path) -> list[Path]:
    """Dossiers resultats/<outil>-<date> qui portent la date la plus récente."""
    dates = {}
    for d in resultats.glob("*-*") if resultats.is_dir() else []:
        m = DATE_PASSAGE.search(d.name)
        if d.is_dir() and m:
            dates.setdefault(m.group(1), []).append(d)
    return sorted(dates[max(dates)]) if dates else []


def fichiers_a_verifier() -> list[Path]:
    fichiers = [f for d in dossiers_du_dernier_passage(RACINE / "resultats") for f in sorted(d.rglob("*"))
                if f.is_file() and f.suffix.lower() in EXTENSIONS]
    page = RACINE / "suivi-barometre.html"
    return fichiers + ([page] if page.is_file() else [])


def trouver(texte: str) -> list[str]:
    trouves = [m.group(0) for m in EMAIL.finditer(texte) if not AUTORISES.search(m.group(0))]
    return trouves + [m.group(0) for m in TELEPHONE.finditer(texte)]


def main() -> int:
    fichiers = fichiers_a_verifier()
    if not fichiers:
        print("✖ Aucun fichier du dernier passage ni suivi-barometre.html : rien n'a été vérifié.", file=sys.stderr)
        return CODE_RIEN_A_VERIFIER
    problemes = []
    for f in fichiers:
        for n, ligne in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            problemes += [f"{f.relative_to(RACINE)}:{n} : « {x} »" for x in trouver(ligne)]
    for p in problemes:
        print(f"✖ Donnée personnelle possible : {p}", file=sys.stderr)
    print(f"{len(fichiers)} fichier(s) vérifié(s), {len(problemes)} donnée(s) personnelle(s) possible(s).")
    return CODE_TROUVE if problemes else 0


if __name__ == "__main__":
    sys.exit(main())
