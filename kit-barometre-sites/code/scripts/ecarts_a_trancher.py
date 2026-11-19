#!/usr/bin/env python3
"""Écarts entre sources restés sans décision, et écarts à arbitrer, dans la dernière lecture critique.

Un écart est sans décision quand son statut n'est ni C, ni NC, ni NA (hors constats généraux, règle « - »). Il se
tranche dans ANALYSE_SOURCES (scripts/lecture_critique.py), puis on relance l'étape synthese. Un écart « à arbitrer »
a un statut retenu selon le protocole, mais attend l'avis de la personne responsable du baromètre.

Entrée : resultats/lecture-critique-*/lecture.json (le dernier), ou --lecture <fichier>.
Codes de sortie : 0 aucun écart sans décision (il peut rester des écarts à arbitrer) ; 1 il en reste ; 2 aucune
lecture critique (lancer d'abord l'étape synthese).

Usage :
  python3 scripts/ecarts_a_trancher.py              # deux listes courtes
  python3 scripts/ecarts_a_trancher.py --dossier    # une fiche compacte par écart, à présenter un par un
  python3 scripts/ecarts_a_trancher.py --dossier --site "Ma boutique"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
import parc  # noqa: E402

DECIDES = ("C", "NC", "NA")
LIB = {"C": "conforme", "NC": "non conforme", "NA": "non applicable", "NT": "non testé", "": "aucun"}
COURT = 400


def charger(chemin: Path | None) -> tuple[Path | None, dict]:
    if chemin is None:
        l = sorted(RACINE.glob("resultats/lecture-critique-*/lecture.json"))
        chemin = l[-1] if l else None
    if chemin is None or not chemin.is_file():
        return None, {}
    return chemin, json.loads(chemin.read_text(encoding="utf-8"))


def ecarts(lecture: dict, site: str | None = None) -> tuple[list, list]:
    """(sans décision, à arbitrer) : listes de (site, écart, verdicts de toutes les sources pour la règle)."""
    sans, arb = [], []
    for s, v in lecture.items():
        if s.startswith("_") or (site and s != site):
            continue
        for e in v.get("ecarts", []):
            if e.get("regle") == "-":
                continue
            verdicts = v.get("recoupement", {}).get(str(e["regle"])) or dict(e.get("base", []))
            if e.get("statut") not in DECIDES:
                sans.append((s, e, verdicts))
            elif e.get("a_arbitrer"):
                arb.append((s, e, verdicts))
    return sans, arb


def court(t: str) -> str:
    t = " ".join(str(t).split())
    return t if len(t) <= COURT else t[:COURT - 1] + "…"


def fiche(i: int, n: int, s: str, e: dict, verdicts: dict, sans: bool) -> str:
    st = e.get("statut", "")
    lignes = [f"[{i}/{n}] {s}, règle {e['regle']} : {e.get('titre', '')}",
              f"  Type : {e.get('type', '')} ; statut {'provisoire' if sans else 'retenu'} : {LIB.get(st, st)}"
              + ("" if sans else " ; à arbitrer"),
              "  Sources et verdicts : " + (" | ".join(f"{a} = {LIB.get(x, x)}" for a, x in sorted(verdicts.items())) or "aucune"),
              f"  Preuves : {court(e.get('constat', ''))}",
              f"  Analyse : {court(e.get('pourquoi', ''))}",
              f"  Que faire : {court(e.get('recommandation', ''))}"]
    if sans:
        lignes.append(f"  Décision à écrire : ANALYSE_SOURCES[(\"{s}\", \"{e['regle']}\")] = (type, statut, pourquoi, que faire, "
                      "à arbitrer) dans scripts/lecture_critique.py")
    return "\n".join(lignes)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dossier", action="store_true", help="une fiche compacte par écart (règle, site, sources, preuves)")
    ap.add_argument("--site", help="un seul site")
    ap.add_argument("--lecture", type=Path, help="lecture.json à lire (défaut : la dernière)")
    a = ap.parse_args(argv)
    chemin, lecture = charger(a.lecture)
    if chemin is None:
        print("Aucune lecture critique (resultats/lecture-critique-*/lecture.json) : lancer d'abord "
              "python3 scripts/barometre.py --hors <hors> --etapes synthese.", file=sys.stderr)
        return 2
    sans, arb = ecarts(lecture, a.site)
    qui = parc.responsable(RACINE)
    print(f"Lecture critique : {chemin.relative_to(RACINE) if chemin.is_relative_to(RACINE) else chemin}")
    if a.dossier:
        tous = [(x, True) for x in sans] + [(x, False) for x in arb]
        print(f"{len(sans)} écart(s) sans décision, {len(arb)} à arbitrer par {qui}. Présenter les fiches une par une.\n")
        for i, ((s, e, v), est_sans) in enumerate(tous, 1):
            print(fiche(i, len(tous), s, e, v, est_sans) + "\n")
    else:
        print(f"Écarts sans décision : {len(sans)}")
        for s, e, _ in sans:
            print(f"  {s}, règle {e['regle']} ({e.get('type', '')}) : {e.get('titre', '')}")
        print(f"Écarts à arbitrer par {qui} : {len(arb)}")
        for s, e, _ in arb:
            print(f"  {s}, règle {e['regle']} (retenu : {LIB.get(e['statut'], e['statut'])}) : {e.get('titre', '')}")
    if sans:
        print("Trancher chaque écart dans ANALYSE_SOURCES (scripts/lecture_critique.py), puis relancer --etapes synthese"
              + ("." if a.dossier else " ; fiches : --dossier."))
    return 1 if sans else 0


if __name__ == "__main__":
    sys.exit(main())
