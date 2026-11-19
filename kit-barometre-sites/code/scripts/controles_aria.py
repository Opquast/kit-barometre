#!/usr/bin/env python3
"""Règles 185 et 244 tirées des résultats déjà mesurés (aucune nouvelle requête vers les sites).

- 185 « Un contenu qui doit être restitué dans un lecteur d'écran ne lui est pas dissimulé » :
  axe-core (aria-hidden-focus) et IBM Equal Access (aria_hidden_nontabbable) : un élément atteignable au clavier
  mais masqué aux lecteurs d'écran. Non conforme si l'un des deux le relève sur la page ; conforme si au moins
  un des deux a analysé la page sans le relever ; non testé sinon.
- 244 « La linéarisation des tableaux utilisés pour la mise en page ne nuit pas à la compréhension » :
  relevé navigateur (liste des tableaux de la page) et IBM (table_layout_linearized). Non applicable sans tableau.

Ces deux règles figuraient dans le volet « page » sans être mesurées (incohérence corrigée le 12/11).

Sortie : resultats/aria-AAAA-MM-JJ/resultats.json, au format de controles_reseau.py (lu par fusion_scripts.py).
Usage : python3 scripts/controles_aria.py
"""
from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

RACINE = Path(__file__).resolve().parent.parent


def dernier(motif: str) -> dict:
    l = sorted(RACINE.glob(motif))
    return json.loads(l[-1].read_text(encoding="utf-8")) if l else {}


def main() -> None:
    axe = dernier("resultats/axe-*/resultats.json").get("sites", {})
    outils = dernier("resultats/outils-*/pages.json")
    releve = dernier("resultats/releve-*/releve.json")
    ecrans = list(csv.DictReader((RACINE / "scripts" / "ecrans_en_ligne.csv").open(encoding="utf-8")))
    services: dict = {}
    for e in ecrans:
        nom, url = e["service"], e["url"]
        chemin = urlsplit(url).path or "/"
        if urlsplit(url).query:
            chemin += "?" + urlsplit(url).query
        pa = next((p for p in axe.get(nom, {}).get("pages", []) if p.get("chemin") == chemin), None)
        ib = outils.get(nom, {}).get("pages", {}).get(url, {}).get("ibm")
        rl = releve.get(nom, {}).get(url) if isinstance(releve.get(nom), dict) else None
        if rl is None and isinstance(releve.get(nom), dict):
            rl = releve[nom].get("pages", {}).get(url)
        c = []
        # 185
        axe_ok = bool(pa and pa.get("teste"))
        axe_nc = axe_ok and any(v["regle"] == "aria-hidden-focus" for v in pa.get("violations", []))
        ib_ok = bool(ib and "par_regle" in ib)
        ib_n = (ib or {}).get("par_regle", {}).get("aria_hidden_nontabbable", 0)
        if axe_nc or ib_n:
            st, com = "non-conforme", "Élément atteignable au clavier mais masqué aux lecteurs d'écran (aria-hidden) : " + \
                ", ".join(x for x in [("axe-core aria-hidden-focus" if axe_nc else ""), (f"IBM aria_hidden_nontabbable ({ib_n})" if ib_n else "")] if x) + "."
        elif axe_ok or ib_ok:
            st, com = "conforme", "Aucun contenu atteignable masqué aux lecteurs d'écran (" + " et ".join(x for x in [("axe-core" if axe_ok else ""), ("IBM" if ib_ok else "")] if x) + ")."
        else:
            st, com = "non-testé", "Page non analysée par axe-core ni par IBM."
        c.append({"rule_number": 185, "status": st, "comment": com})
        # 244
        if rl is None and not ib_ok:
            c.append({"rule_number": 244, "status": "non-testé", "comment": "Page absente du relevé et non analysée par IBM."})
        else:
            tab = (rl or {}).get("tableaux", [])
            ib_t = (ib or {}).get("par_regle", {}).get("table_layout_linearized", 0)
            if ib_t:
                c.append({"rule_number": 244, "status": "non-conforme", "comment": f"IBM table_layout_linearized : {ib_t} tableau(x) de mise en page mal linéarisé(s)."})
            elif not tab:
                c.append({"rule_number": 244, "status": "non-applicable", "comment": "Aucun tableau dans la page (relevé navigateur" + (", IBM sans défaut" if ib_ok else "") + ")."})
            else:
                c.append({"rule_number": 244, "status": "conforme" if ib_ok else "non-testé",
                          "comment": f"{len(tab)} tableau(x) ; IBM ne relève aucun défaut de linéarisation." if ib_ok else f"{len(tab)} tableau(x), linéarisation non vérifiée."})
        services.setdefault(nom, {"pages": [], "site": []})["pages"].append({"gabarit": e["gabarit"], "url": url, "controles": c})
    sortie = RACINE / "resultats" / f"aria-{date.today():%Y-%m-%d}"
    sortie.mkdir(parents=True, exist_ok=True)
    meta = {"script": "scripts/controles_aria.py", "date": date.today().isoformat(), "sources": "axe-core, IBM Equal Access, relevé navigateur"}
    (sortie / "resultats.json").write_text(json.dumps({"meta": meta, "services": services}, ensure_ascii=False, indent=1), encoding="utf-8")
    for nom, s in services.items():
        from collections import Counter
        print(nom, {n: dict(Counter(c["status"] for p in s["pages"] for c in p["controles"] if c["rule_number"] == n)) for n in (185, 244)})


if __name__ == "__main__":
    main()
