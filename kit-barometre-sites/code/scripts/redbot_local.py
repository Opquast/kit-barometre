#!/usr/bin/env python3
"""Passe les écrans du baromètre à REDbot (https://redbot.org/), installé en local.

redbot.org demande une vérification humaine (Cloudflare) : on ne la contourne pas. REDbot étant open source,
on utilise sa version en ligne de commande, mêmes contrôles (paquet Python `redbot`, dans .venv :
`python3 -m venv .venv && .venv/bin/pip install redbot`). REDbot envoie quelques requêtes par page
(requête simple, négociation gzip, requête conditionnelle) et note chaque en-tête : GOOD, WARN, BAD, INFO.

Règles Opquast déduites des notes de REDbot (les autres notes restent dans le rapport, pour information) :
- 206 : en-tête X-Content-Type-Options: nosniff (CONTENT_TYPE_OPTIONS) ;
- 211 : protection contre l'affichage dans un cadre (FRAME_OPTIONS_*) ;
- 226 : compression des contenus (CONNEG_GZIP_GOOD / CONNEG_NO_GZIP, CONNEG_GZIP_BAD) ;
- 227 : informations de mise en cache (Cache-Control, validateurs ETag ou Last-Modified) ;
- 228 : jeu de caractères dans l'en-tête Content-Type.
199 (HSTS) et 212 (CSP) ne sont pas reprises : REDbot juge la présence de l'en-tête, nos contrôles réseau
(v0.2.0) sont plus exigeants (durée d'un an, restriction d'origine).

Une page toutes les 10 secondes. Les comptes clients hébergés par Shopify ne sont pas testés.
Sortie : resultats/redbot-AAAA-MM-JJ/ (resultats.json au format des contrôles réseau, rapport.md, har/).

Usage : python3 scripts/redbot_local.py [--delai 10] [--service "Boutique A"]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import parc

RACINE = Path(__file__).resolve().parent.parent
REDBOT = RACINE / ".venv" / "bin" / "redbot"
VERSION = "0.1.0"


def lancer(url: str) -> dict:
    sortie = subprocess.run([str(REDBOT), "-o", "har", "-t", "60", url], capture_output=True, text=True, timeout=120)
    return json.loads(sortie.stdout)


def regles(notes: list[dict], reponse: dict) -> list[dict]:
    ids = {n.get("note_id") for n in notes}
    entetes = {h["name"].lower(): h["value"] for h in reponse.get("headers", [])}
    out = []

    def res(n, ok, com, preuve=""):
        out.append({"rule_number": n, "status": "conforme" if ok else "non-conforme", "comment": f"REDbot : {com}", "evidence": preuve})

    res(206, "CONTENT_TYPE_OPTIONS" in ids, "X-Content-Type-Options: nosniff " + ("présent" if "CONTENT_TYPE_OPTIONS" in ids else "absent"),
        entetes.get("x-content-type-options", ""))
    cadre = {i for i in ids if i and i.startswith("FRAME_OPTIONS")} | ({"CSP_FRAME"} if "frame-ancestors" in entetes.get("content-security-policy", "") else set())
    res(211, bool(cadre - {"FRAME_OPTIONS_NOT"}), "protection contre les cadres : " + (", ".join(sorted(cadre)) or "aucune"),
        entetes.get("x-frame-options", ""))
    if ids & {"CONNEG_GZIP_GOOD", "CONNEG_GZIP_BAD", "CONNEG_NO_GZIP"} or "content-encoding" in entetes:
        res(226, "CONNEG_GZIP_GOOD" in ids or entetes.get("content-encoding") in ("gzip", "br", "zstd"),
            "compression " + ("négociée" if "CONNEG_GZIP_GOOD" in ids else "non négociée"), entetes.get("content-encoding", ""))
    cc = entetes.get("cache-control", "")
    valid = "etag" in entetes or "last-modified" in entetes
    res(227, bool(cc) or valid, f"Cache-Control « {cc or 'absent'} », validateur {'présent' if valid else 'absent'}"
        + (" ; page HTML non mise en cache (max-age=0)" if "max-age=0" in cc else ""), cc)
    ct = entetes.get("content-type", "")
    res(228, "charset=" in ct.lower(), f"Content-Type « {ct or 'absent'} »", ct)
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--delai", type=float, default=10)
    p.add_argument("--service")
    args = p.parse_args()
    debut = datetime.now().astimezone()
    sortie = RACINE / "resultats" / f"redbot-{debut:%Y-%m-%d}"
    (sortie / "har").mkdir(parents=True, exist_ok=True)
    ecrans = [e for e in csv.DictReader((RACINE / "scripts" / "ecrans_en_ligne.csv").open(encoding="utf-8"))
              if not args.service or e["service"] == args.service]
    services: dict[str, dict] = {}
    hors_site = parc.hors_site()  # sites dont le compte client (/account) est hébergé hors du site
    for i, e in enumerate(ecrans):
        fiche = {"gabarit": e["gabarit"], "url": e["url"], "controles": [], "notes": []}
        services.setdefault(e["service"], {"pages": []})["pages"].append(fiche)
        if e["service"] in hors_site and urllib.parse.urlsplit(e["url"]).path.endswith("/account"):
            fiche["non_teste"] = "compte client hébergé hors du site"
            continue
        if i:
            time.sleep(args.delai)
        try:
            har = lancer(e["url"])
            entree = har["log"]["entries"][0]
        except Exception as ex:
            fiche["non_teste"] = f"REDbot : {ex}"
            print(f"{e['service']} | {e['gabarit']} | non testé ({ex})")
            continue
        statut = entree["response"].get("status")
        nom = re.sub(r"[^a-z0-9]+", "-", f"{e['service']}-{e['gabarit']}".lower()).strip("-")[:60]
        (sortie / "har" / f"{nom}.har").write_text(json.dumps(har, ensure_ascii=False), encoding="utf-8")
        notes = entree.get("_red_messages", [])
        fiche["statut_http"] = statut
        fiche["notes"] = [{"niveau": n.get("level"), "id": n.get("note_id"), "resume": n.get("summary")} for n in notes]
        if statut == 429 or (statut or 0) >= 400:
            fiche["non_teste"] = f"code {statut} (page refusée au robot)"
        else:
            fiche["controles"] = regles(notes, entree["response"])
        nc = [c["rule_number"] for c in fiche["controles"] if c["status"] != "conforme"]
        print(f"{e['service']} | {e['gabarit']} | {fiche.get('non_teste') or ('non conformes : ' + ', '.join(map(str, nc)) if nc else 'conforme')}")

    meta = {"script": "scripts/redbot_local.py", "version": VERSION, "date": debut.isoformat(timespec="seconds"),
            "outil": "REDbot (paquet Python, en local)", "delai_s": args.delai, "referentiel": "Opquast V5 qualite-numerique"}
    (sortie / "resultats.json").write_text(json.dumps({"meta": meta, "services": services}, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# En-têtes HTTP (REDbot) du {debut:%Y-%m-%d}", "",
          "REDbot en local (redbot.org demande une vérification humaine). Règles Opquast déduites : 206, 211, 226, 227, 228.", "",
          "| Site | Pages testées | 206 | 211 | 226 | 227 | 228 | Notes BAD / WARN |", "|---|---|---|---|---|---|---|---|"]
    for nom, s in services.items():
        t = [pg for pg in s["pages"] if pg["controles"]]
        cell = []
        for n in (206, 211, 226, 227, 228):
            st = [c["status"] for pg in t for c in pg["controles"] if c["rule_number"] == n]
            k = st.count("non-conforme")
            cell.append(f"**{k} NC** / {len(st)}" if k else f"C ({len(st)})" if st else "")
        bad = sum(1 for pg in t for n in pg["notes"] if n["niveau"] == "BAD")
        warn = sum(1 for pg in t for n in pg["notes"] if n["niveau"] == "WARN")
        md.append(f"| {nom} | {len(t)} sur {len(s['pages'])} | " + " | ".join(cell) + f" | {bad} / {warn} |")
    md += ["", "## Notes BAD et WARN de REDbot, par type", ""]
    vues: dict[str, set] = {}
    for nom, s in services.items():
        for pg in s["pages"]:
            for n in pg["notes"]:
                if n["niveau"] in ("BAD", "WARN"):
                    vues.setdefault(f"{n['niveau']} {n['id']} : {n['resume']}", set()).add(nom)
    md += [f"- {k} ({len(v)} site(s))" for k, v in sorted(vues.items())] + [""]
    md += [f"- {nom}, {pg['gabarit']} : non testé ({pg['non_teste']})." for nom, s in services.items() for pg in s["pages"] if pg.get("non_teste")]
    (sortie / "rapport.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{sortie} : {len(ecrans)} écrans")


if __name__ == "__main__":
    main()
