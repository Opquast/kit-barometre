#!/usr/bin/env python3
"""Prépare l'import de nos résultats dans eServices Manager (bouton « Importer » de « Nouvel audit »).

Une ligne par page et par critère, au format du modèle audit-import-template.xlsx :
SERVICE_SHORT_CODE, RULE_SHORT_CODE, CONTROL_RESULT, CONTROL_COMMENT, PAGE_SHORT_CODE, PAGE_TITLE,
PAGE_URL, AUDITOR_SHORT_CODE, CONTROL_DATE.

Source prise en charge : contrôles réseau (`resultats/reseau-AAAA-MM-JJ/resultats.json`), critères `opquast-N`
de la checklist « Opquast scripts, 82 règles ». Les règles de niveau site (certificat, DNS, robots.txt…) sont
rattachées à la page d'accueil. Les résultats « non testé » ne sont pas importés.

Usage : python3 scripts/import_esm.py resultats/reseau-2026-11-12
Sortie : un fichier import-esm-<CODE>.csv par service dans le même dossier.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SERVICES = {  # nom -> (code du service dans ESM, préfixe des codes de page)
    "Boutique A": ("WEB-BOUTIQUEA", "BM"), "Boutique B": ("WEB-BOUTIQUEB", "MAG"),
    "Boutique C": ("WEB-BOUTIQUEC", "BOUTIQUEC"), "Boutique D": ("WEB-BOUTIQUED", "DDM"),
    "Boutique E": ("WEB-BOUTIQUEE", "TDA"), "Boutique F": ("WEB-BOUTIQUEF", "MAJ"),
}
RESULTAT = {"conforme": "C", "non conforme": "NC", "non applicable": "NA"}
AUDITEUR = "MLU"  # code court de Mattea dans eServices Manager (Paramètres > Utilisateurs)
ENTETE = ["SERVICE_SHORT_CODE", "RULE_SHORT_CODE", "CONTROL_RESULT", "CONTROL_COMMENT", "PAGE_SHORT_CODE",
          "PAGE_TITLE", "PAGE_URL", "AUDITOR_SHORT_CODE", "CONTROL_DATE"]


def code_page(prefixe: str, gabarit: str) -> str:
    """Même règle que lors de l'import des pages : préfixe + gabarit en majuscules, sans la parenthèse."""
    if gabarit.startswith("Accueil"):
        return ""  # la page d'accueil créée avec le service n'a pas de code court : on la retrouve par son URL
    g = gabarit.split(" (")[0].upper().replace(" ", "-")
    return f"{prefixe}-" + "".join(c for c in g if c.isalnum() or c == "-")


def titre_page(gabarit: str) -> str:
    return "Accueil" if gabarit.startswith("Accueil") else gabarit


def main() -> None:
    dossier = Path(sys.argv[1] if len(sys.argv) > 1 else "resultats/reseau-2026-11-12")
    d = json.loads((dossier / "resultats.json").read_text(encoding="utf-8"))
    date = d["meta"]["date"][:10]
    version = d["meta"]["version"]
    ecrans = {(r["service"], r["url"]): r["gabarit"] for r in csv.DictReader((RACINE / "scripts" / "ecrans_en_ligne.csv").open(encoding="utf-8"))}
    for nom, v in d["services"].items():
        code_service, prefixe = SERVICES[nom]
        accueil = next(p for p in v["pages"] if p["gabarit"].startswith("Accueil"))
        lignes = []

        def ajoute(page: dict, c: dict) -> None:
            res = RESULTAT.get(c["status"].replace("-", " "))
            if not res:
                return
            gab = ecrans.get((nom, page["url"]), page["gabarit"])
            com = re.sub(r"mailto:[^;,\s]+", "mailto:[masqué]", f"{c['comment']} {c.get('evidence', '')}".strip())
            lignes.append([code_service, f"opquast-{c['rule_number']}", res,
                           f"[controles_reseau.py v{version}] {com}"[:1000], code_page(prefixe, gab), titre_page(gab),
                           page["url"], AUDITEUR, date])

        for c in v.get("site", []):
            ajoute(accueil, c)
        for p in v["pages"]:
            for c in p.get("controles", []):
                ajoute(p, c)
        sortie = dossier / f"import-esm-{code_service}.csv"
        with sortie.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(ENTETE)
            w.writerows(lignes)
        print(f"{sortie.name} : {len(lignes)} lignes")


if __name__ == "__main__":
    main()
