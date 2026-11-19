"""Repère les données personnelles dans les fichiers CSV et Excel versionnés.

Cherche les adresses e-mail (hors domaines d'exemple), les numéros de téléphone
français et les colonnes nominatives (nom, prénom, e-mail, téléphone) remplies.
Code de sortie 1 si quelque chose est trouvé.
"""

from __future__ import annotations

import csv
import io
import re
import sys
from pathlib import Path

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}")
TELEPHONE = re.compile(r"(?<![\d.,])(?:\+33 ?|0)[1-9](?:[ .-]?\d{2}){4}(?![\d.,])")
DOMAINES_EXEMPLE = ("example.com", "example.org", "example.net", "exemple.fr", "exemple.com")
COLONNES_NOMINATIVES = {
    "nom", "prenom", "prénom", "nom_complet", "email", "e-mail", "courriel", "mail",
    "telephone", "téléphone", "tel", "tél", "mobile", "portable",
}


def email_autorise(adresse: str) -> bool:
    domaine = adresse.rsplit("@", 1)[1].lower()
    return any(domaine == d or domaine.endswith("." + d) for d in DOMAINES_EXEMPLE)


def controler_cellule(valeur: str) -> list[str]:
    problemes = []
    for m in EMAIL.finditer(valeur):
        if not email_autorise(m.group(0)):
            problemes.append(f"adresse e-mail « {m.group(0)} »")
    for m in TELEPHONE.finditer(valeur):
        problemes.append(f"numéro de téléphone « {m.group(0)} »")
    return problemes


def controler_lignes(lignes: list[list[str]]) -> list[str]:
    """Contrôle un tableau dont la première ligne est l'en-tête."""
    if not lignes:
        return []
    entete = [str(c or "").strip().lstrip("﻿").lower() for c in lignes[0]]
    nominatives = {i for i, nom in enumerate(entete) if nom in COLONNES_NOMINATIVES}
    problemes = []
    for n, ligne in enumerate(lignes, start=1):
        for i, cellule in enumerate(ligne):
            valeur = "" if cellule is None else str(cellule)
            for p in controler_cellule(valeur):
                problemes.append(f"ligne {n} : {p}")
            if n > 1 and i in nominatives and valeur.strip():
                problemes.append(f"ligne {n} : colonne nominative « {entete[i]} » remplie")
    return problemes


def lire_csv(chemin: Path) -> list[list[str]]:
    texte = chemin.read_text(encoding="utf-8-sig", errors="replace")
    try:
        dialecte = csv.Sniffer().sniff(texte[:4096], delimiters=";,\t")
    except csv.Error:
        dialecte = csv.excel
    return list(csv.reader(io.StringIO(texte), dialecte))


def lire_excel(chemin: Path) -> dict[str, list[list[str]]]:
    import openpyxl

    classeur = openpyxl.load_workbook(chemin, read_only=True, data_only=True)
    try:
        return {f.title: [list(r) for r in f.iter_rows(values_only=True)] for f in classeur.worksheets}
    finally:
        classeur.close()


def controler_fichier(chemin: Path) -> list[str]:
    suffixe = chemin.suffix.lower()
    if suffixe in (".csv", ".tsv"):
        return [f"{chemin} {p}" for p in controler_lignes(lire_csv(chemin))]
    if suffixe in (".xlsx", ".xlsm"):
        return [
            f"{chemin} [{feuille}] {p}"
            for feuille, lignes in lire_excel(chemin).items()
            for p in controler_lignes(lignes)
        ]
    return []


def main(arguments: list[str]) -> int:
    problemes = [p for a in arguments for p in controler_fichier(Path(a))]
    for p in problemes:
        print(f"✖ Donnée personnelle : {p}", file=sys.stderr)
    return 1 if problemes else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
