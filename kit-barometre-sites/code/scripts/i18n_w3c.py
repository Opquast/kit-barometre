#!/usr/bin/env python3
"""Passe les écrans du baromètre au W3C Internationalization Checker (https://validator.w3.org/i18n-checker/).

Le service du W3C lit lui-même chaque page et rend un rapport : codage des caractères (en-tête HTTP, BOM, balise meta),
langue (attribut lang, en-tête Content-Language), direction du texte, puis remarques classées Error, Warning ou Info.
Le script en déduit, de façon déterministe, le statut de 4 règles Opquast :

- 130 : le code source indique la langue principale (attribut lang présent, aucune erreur de langue) ;
- 228 : l'en-tête HTTP Content-Type indique le jeu de caractères ;
- 232 : une balise meta définit le jeu de caractères (et tient dans les 1 024 premiers octets, exigence HTML5) ;
- 233 : le codage utilisé est UTF-8.

Une requête toutes les 15 secondes (service public, partagé). Les comptes clients hébergés par Shopify, hors du site,
ne sont pas envoyés. Sortie : resultats/i18n-AAAA-MM-JJ/ (resultats.json au format des contrôles réseau, rapport.md).

Usage : python3 scripts/i18n_w3c.py [--delai 15] [--service "Boutique A"]
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
VERSION = "0.1.0"
UA = f"Opquast-barometre-Colorz/{VERSION} (i18n checker, lecture seule)"
SERVICE = "https://validator.w3.org/i18n-checker/check?uri="
HORS_SITE = re.compile(r"/account$")  # comptes clients redirigés vers shopify.com sur 3 sites


def texte(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def analyser(page: str) -> dict:
    """Extrait du rapport HTML les valeurs du tableau d'information et les remarques détaillées."""
    info = {}
    for ligne in re.findall(r"<tr>(.*?)</tr>", page, re.S):
        cases = re.findall(r"<td[^>]*>(.*?)</td>", ligne, re.S)
        if len(cases) >= 2:
            info.setdefault(texte(cases[0]), (texte(cases[1]), texte(cases[2]) if len(cases) > 2 else ""))
    remarques = []
    for m in re.finditer(r'<h2 class="title" title="([^"]+)">\s*<img[^>]*alt="(\w+)"[^>]*/>(.*?)</h2>', page, re.S):
        remarques.append({"code": m.group(1), "gravite": m.group(2), "titre": texte(m.group(3))})
    return {"info": info, "remarques": remarques, "tidy": "run through the HTML Tidy" in page}


def statuts(a: dict) -> list[dict]:
    info, rem = a["info"], a["remarques"]
    err = [r for r in rem if r["gravite"] == "Error"]
    out = []

    def res(n, ok, com, preuve=""):
        out.append({"rule_number": n, "status": "conforme" if ok else "non-conforme", "comment": com, "evidence": preuve})

    lang, lang_code = info.get("HTML tag", ("", ""))
    err_lang = [r for r in err if "lang" in r["code"]]
    res(130, bool(lang) and lang.lower() != "none found" and not err_lang,
        f"Attribut lang : {lang or 'absent'}" + (f" ; erreurs : {'; '.join(r['titre'] for r in err_lang)}" if err_lang else ""), lang_code)

    http, http_code = info.get("HTTP Content-Type", ("", ""))
    res(228, "charset" in http_code.lower() or (bool(http) and http.lower() != "none found"),
        f"Jeu de caractères dans l'en-tête HTTP : {http or 'absent'}", http_code)

    meta, meta_code = info.get("Meta tag", ("", ""))
    err_meta = [r for r in err if "charset" in r["code"] and "utf" not in r["code"]]
    res(232, bool(meta) and meta.lower() != "none found" and not err_meta,
        f"Balise meta : {meta or 'absente'}" + (f" ; erreur W3C : {'; '.join(r['titre'] for r in err_meta)}" if err_meta else ""), meta_code)

    # une valeur peut contenir plusieurs déclarations (« utf-8 utf-8 ») : on juge chaque jeton (corrigé le 12/11)
    valeurs = {t for v in (http, meta) if v and v.lower() != "none found" for t in v.lower().replace(",", " ").split()}
    err_utf = [r for r in err if "utf" in r["code"]]
    res(233, bool(valeurs) and valeurs <= {"utf-8"} and not err_utf, f"Codage déclaré : {', '.join(sorted(valeurs)) or 'aucun'}")
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--delai", type=float, default=15)
    p.add_argument("--service")
    args = p.parse_args()
    debut = datetime.now().astimezone()
    sortie = RACINE / "resultats" / f"i18n-{debut:%Y-%m-%d}"
    sortie.mkdir(parents=True, exist_ok=True)
    ecrans = [e for e in csv.DictReader((RACINE / "scripts" / "ecrans_en_ligne.csv").open(encoding="utf-8"))
              if not args.service or e["service"] == args.service]
    services: dict[str, dict] = {}
    for i, e in enumerate(ecrans):
        fiche = {"gabarit": e["gabarit"], "url": e["url"], "controles": [], "remarques": []}
        services.setdefault(e["service"], {"pages": []})["pages"].append(fiche)
        if HORS_SITE.search(urllib.parse.urlsplit(e["url"]).path) and e["service"] in ("Boutique C", "Boutique D", "Boutique E"):
            fiche["non_teste"] = "compte client hébergé par Shopify, hors du site"
            continue
        if i:
            time.sleep(args.delai)
        try:
            req = urllib.request.Request(SERVICE + urllib.parse.quote(e["url"], safe=""), headers={"User-Agent": UA})
            page = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")  # nosec B310: URL http(s) du parc ou d'un service connu
        except Exception as ex:  # service indisponible ou page refusée : non testé, sans nouvelle tentative
            fiche["non_teste"] = f"i18n checker : {ex}"
            print(f"{e['service']} | {e['gabarit']} | non testé ({ex})")
            continue
        a = analyser(page)
        if not a["info"]:
            fiche["non_teste"] = "le W3C n'a pas pu lire la page (protection anti-robots probable)"
        else:
            fiche["controles"] = statuts(a)
            fiche["remarques"] = a["remarques"]
            fiche["html_repare_par_tidy"] = a["tidy"]
        nc = [c["rule_number"] for c in fiche["controles"] if c["status"] != "conforme"]
        print(f"{e['service']} | {e['gabarit']} | {fiche.get('non_teste') or ('non conformes : ' + ', '.join(map(str, nc)) if nc else 'conforme')}")

    meta = {"script": "scripts/i18n_w3c.py", "version": VERSION, "date": debut.isoformat(timespec="seconds"),
            "outil": "W3C Internationalization Checker 2.0.3", "delai_s": args.delai, "referentiel": "Opquast V5 qualite-numerique"}
    (sortie / "resultats.json").write_text(json.dumps({"meta": meta, "services": services}, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# Internationalisation (W3C i18n Checker) du {debut:%Y-%m-%d}", "",
          "Chaque écran est passé au service du W3C ; 4 règles Opquast en sont déduites : 130 (langue), 228 (jeu de caractères dans l'en-tête HTTP), 232 (balise meta), 233 (UTF-8).", "",
          "| Site | Pages testées | 130 | 228 | 232 | 233 | Remarques W3C (erreurs / avertissements) |", "|---|---|---|---|---|---|---|"]
    for nom, s in services.items():
        t = [pg for pg in s["pages"] if pg["controles"]]
        cell = []
        for n in (130, 228, 232, 233):
            st = [c["status"] for pg in t for c in pg["controles"] if c["rule_number"] == n]
            k = st.count("non-conforme")
            cell.append(f"**{k} NC** / {len(st)}" if k else f"C ({len(st)})")
        er = sum(1 for pg in t for r in pg["remarques"] if r["gravite"] == "Error")
        wa = sum(1 for pg in t for r in pg["remarques"] if r["gravite"] == "Warning")
        md.append(f"| {nom} | {len(t)} sur {len(s['pages'])} | " + " | ".join(cell) + f" | {er} / {wa} |")
    md += ["", "## Remarques du W3C, par type", ""]
    vues: dict[str, set] = {}
    for nom, s in services.items():
        for pg in s["pages"]:
            for r in pg["remarques"]:
                vues.setdefault(f"{r['gravite']} : {r['titre']}", set()).add(nom)
    md += [f"- {k} ({', '.join(sorted(v))})" for k, v in sorted(vues.items())] + [""]
    md += [f"- {nom}, {pg['gabarit']} : non testé ({pg['non_teste']})." for nom, s in services.items() for pg in s["pages"] if pg.get("non_teste")]
    (sortie / "rapport.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{sortie} : {len(ecrans)} écrans")


if __name__ == "__main__":
    main()
