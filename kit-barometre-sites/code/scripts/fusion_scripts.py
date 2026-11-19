#!/usr/bin/env python3
"""Fusionne, page par page et règle par règle, les résultats de nos contrôles sans IA, pour eServices Manager.

Sources (dernier passage de chaque outil) :
- contrôles réseau  : resultats/reseau-*/resultats.json (règles de niveau site rattachées à la page d'accueil) ;
- code de la page   : resultats/page-*/resultats.json ;
- W3C i18n Checker  : resultats/i18n-*/resultats.json (130, 228, 232, 233) ;
- REDbot            : resultats/redbot-*/resultats.json (206, 211, 226, 227, 228) ;
- aria              : resultats/aria-*/resultats.json (185 et 244, tirées d'axe-core, d'IBM et du relevé).

Règle de fusion : non conforme si au moins une source l'est ; sinon conforme si au moins une l'est ; sinon non
applicable. Les « non testé » ne sont pas reportés. Le commentaire cite chaque source.

Sortie : resultats/esm-scripts-AAAA-MM-JJ/<CODE_SERVICE>.json, une liste de pages
[{ "titre", "url", "resultats": { "<n° de règle>": ["C"|"NC"|"NA", "commentaire"] } }],
saisie ensuite dans l'audit « Opquast scripts, 82 règles » de chaque site (vue Fiches).

Usage : python3 scripts/fusion_scripts.py [source à ignorer…]
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SERVICES = {"Boutique A": "WEB-BOUTIQUEA", "Boutique B": "WEB-BOUTIQUEB", "Boutique C": "WEB-BOUTIQUEC",
            "Boutique D": "WEB-BOUTIQUED", "Boutique E": "WEB-BOUTIQUEE", "Boutique F": "WEB-BOUTIQUEF"}
SOURCES = [("reseau", "controles_reseau.py"), ("page", "controles_page.js"), ("i18n", "W3C i18n Checker"), ("redbot", "REDbot"), ("aria", "axe-core, IBM et relevé")]
SAUF = set(sys.argv[1:])  # sources à ignorer (ex. redbot tant que son passage n'est pas fini)
CODE = {"conforme": "C", "non conforme": "NC", "non applicable": "NA"}


def charger(prefixe: str) -> dict:
    """Résultats du dernier passage de l'outil, service par service (un service absent du dernier passage
    reprend le précédent : les contrôles réseau des 5/11 et 12/11 se complètent)."""
    out: dict = {}
    for f in sorted((RACINE / "resultats").glob(f"{prefixe}-*/resultats.json")):
        if not re.fullmatch(rf"{prefixe}-\d{{4}}-\d{{2}}-\d{{2}}", f.parent.name):
            continue
        if prefixe in SAUF:
            continue
        out.update(json.loads(f.read_text(encoding="utf-8"))["services"])
    return out


def main() -> None:
    regles_82 = {int(x["numero"]) for x in csv.DictReader((RACINE / "referentiel" / "repartition-regles.csv").open(encoding="utf-8"))
                 if x["methode"] in ("réseau", "page")}
    ecrans = list(csv.DictReader((RACINE / "scripts" / "ecrans_en_ligne.csv").open(encoding="utf-8")))
    donnees = {cle: charger(cle) for cle, _ in SOURCES}
    sortie = RACINE / "resultats" / f"esm-scripts-{date.today():%Y-%m-%d}"
    sortie.mkdir(parents=True, exist_ok=True)
    bilan = []
    for nom, code in SERVICES.items():
        pages = []
        for e in [x for x in ecrans if x["service"] == nom]:
            accueil = e["gabarit"].startswith("Accueil")
            vus: dict[int, list] = {}
            for cle, outil in SOURCES:
                s = donnees[cle].get(nom, {})
                controles = []
                for p in s.get("pages", []):
                    if p.get("url") == e["url"]:
                        controles += p.get("controles", [])
                if accueil:
                    controles += s.get("site", [])
                for c in controles:
                    st = CODE.get(c["status"].replace("-", " "))
                    if st and c["rule_number"] in regles_82:
                        com = re.sub(r"mailto:[^;,\s]+", "mailto:[masqué]", c.get("comment", ""))
                        vus.setdefault(c["rule_number"], []).append((st, f"[{outil}] {com}"))
            res = {}
            for n, l in sorted(vus.items()):
                sts = [x[0] for x in l]
                st = "NC" if "NC" in sts else "C" if "C" in sts else "NA"
                res[str(n)] = [st, " | ".join(x[1] for x in l)[:900]]
            pages.append({"titre": "Accueil" if accueil else e["gabarit"], "url": e["url"], "resultats": res})
        (sortie / f"{code}.json").write_text(json.dumps(pages, ensure_ascii=False, indent=1), encoding="utf-8")
        n = sum(len(p["resultats"]) for p in pages)
        nc = sum(1 for p in pages for v in p["resultats"].values() if v[0] == "NC")
        bilan.append(f"{nom} : {n} résultats ({nc} non conformes) sur {len(pages)} pages")
    print("\n".join(bilan))


if __name__ == "__main__":
    main()
