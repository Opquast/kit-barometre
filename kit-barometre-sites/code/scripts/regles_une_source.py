#!/usr/bin/env python3
"""Liste, site par site, les règles restées à une seule source (ou aucune) après la première synthèse.

C'est l'entrée de la lecture 3 (DOM, captures et paiement) décrite dans
.claude/skills/barometre-sites/references/lectures-independantes.md : le sous-agent ne lit que ce fichier, jamais
resultats/ (indépendance) : la liste est donc écrite hors du dépôt, dans le dossier --hors.

Entrée : resultats/lecture-critique-*/lecture.json (dernière synthèse). Sortie : <hors>/regles_une_source.json au
format {"Site": ["12", "34"]}.
Usage : python3 scripts/regles_une_source.py <dossier hors dépôt>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SOURCES_MIN = 2


def main(arguments: list[str]) -> int:
    if len(arguments) != 1:
        print("Usage : python3 scripts/regles_une_source.py <dossier hors dépôt>", file=sys.stderr)
        return 2
    lectures = sorted(RACINE.glob("resultats/lecture-critique-*/lecture.json"))
    if not lectures:
        print("✖ Aucune synthèse (resultats/lecture-critique-*) : lancer d'abord l'étape synthese.", file=sys.stderr)
        return 1
    lecture = json.loads(lectures[-1].read_text(encoding="utf-8"))
    out = {site: [k for k, src in v.get("sources_par_regle", {}).items() if len(src) < SOURCES_MIN]
           for site, v in lecture.items() if not site.startswith("_")}
    sortie = Path(arguments[0]) / "regles_une_source.json"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{sortie} : " + ", ".join(f"{s} {len(r)} règle(s)" for s, r in out.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
