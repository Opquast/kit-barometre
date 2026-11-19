#!/usr/bin/env python3
"""Services en ligne gratuits du support J2, sur le parc du baromètre (bibliothèque standard Python).

- MDN HTTP Observatory (API v2) : note A+ à F et score des en-têtes de sécurité, par site ;
- SSL Labs (Qualys, API v3) : note de la configuration TLS, par site (analyse en cache acceptée, 24 h) ;
- Validateur Nu du W3C : erreurs et avertissements HTML, page par page (une page toutes les 20 s).

Lecture seule ; ces services lisent eux-mêmes les sites publics. Aucune donnée personnelle envoyée.
Sortie : resultats/outils-AAAA-MM-JJ/en_ligne.json
Usage : python3 scripts/outils_en_ligne.py [--sans-nu]
"""
from __future__ import annotations

import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
UA = "Opquast-barometre-Colorz/0.3 (outils en ligne, lecture seule)"


def get(url: str, methode: str = "GET", timeout: int = 90) -> dict:
    req = urllib.request.Request(url, method=methode, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310: URL http(s) du parc ou d'un service connu
        return json.loads(r.read().decode("utf-8", "replace"))


# Pénalité d'Observatory non reproduite sur le code réel des pages (scripts externes tous en HTTPS, le seul en « // »
# porte un attribut integrity) : on la neutralise dans le score corrigé, en gardant le score brut à côté.
NON_REPRODUITES = {"sri-not-implemented-and-external-scripts-not-loaded-securely"}


def observatory(host: str) -> dict:
    d = get("https://observatory-api.mdn.mozilla.net/api/v2/scan?host=" + host, "POST")
    r = {k: d.get(k) for k in ("grade", "score", "tests_passed", "tests_failed", "tests_quantity", "scanned_at", "details_url")}
    t = get("https://observatory-api.mdn.mozilla.net/api/v2/analyze?host=" + host).get("tests") or {}
    r["penalites"] = [[k, v["result"], v["score_modifier"]] for k, v in t.items() if v.get("score_modifier")]
    malus = sum(m for _, res, m in r["penalites"] if m < 0 and res not in NON_REPRODUITES)
    bonus = sum(m for _, _, m in r["penalites"] if m > 0)
    base = 100 + malus
    r["score_corrige"] = max(0, base + (bonus if base >= 90 else 0))
    return r


def ssllabs(host: str) -> dict:
    url = f"https://api.ssllabs.com/api/v3/analyze?host={host}&fromCache=on&maxAge=24&all=done"
    for _ in range(40):
        d = get(url)
        if d.get("status") in ("READY", "ERROR"):
            break
        time.sleep(30)
    eps = d.get("endpoints", [])
    return {"statut": d.get("status"), "notes": sorted({e.get("grade", "?") for e in eps}), "serveurs": len(eps),
            "message": d.get("statusMessage", ""), "details_url": f"https://www.ssllabs.com/ssltest/analyze.html?d={host}"}


def nu(url: str) -> dict:
    d = get("https://validator.w3.org/nu/?out=json&doc=" + urllib.parse.quote(url, safe=""))
    msgs = d.get("messages", [])
    if not msgs or any(m["type"] == "non-document-error" for m in msgs):
        # le validateur n'a pas pu lire la page (refus, limite d'appels) : surtout pas « 0 erreur »
        raise RuntimeError("page non lue par le validateur : " + (msgs[0].get("message", "réponse vide")[:80] if msgs else "réponse vide"))
    err = [m for m in msgs if m["type"] == "error"]
    av = [m for m in msgs if m["type"] == "info" and m.get("subType") == "warning"]
    top = Counter(m["message"].split("“")[0].strip()[:90] for m in err).most_common(5)
    return {"erreurs": len(err), "avertissements": len(av), "principales": top,
            "details_url": "https://validator.w3.org/nu/?doc=" + urllib.parse.quote(url, safe="")}


def main() -> None:
    ecrans = list(csv.DictReader((RACINE / "scripts" / "ecrans_en_ligne.csv").open(encoding="utf-8")))
    sortie = RACINE / "resultats" / f"outils-{date.today():%Y-%m-%d}"
    sortie.mkdir(parents=True, exist_ok=True)
    fichier = sortie / "en_ligne.json"
    res = json.loads(fichier.read_text(encoding="utf-8")) if fichier.exists() else {}
    hotes = {}
    for e in ecrans:
        hotes.setdefault(e["service"], urllib.parse.urlsplit(e["url"]).hostname)
    for nom, h in hotes.items():
        s = res.setdefault(nom, {"hote": h})
        for cle, f in (("ssllabs", ssllabs),):  # Observatory retiré le 12/11 : doublon des règles 199 et 212, pénalité −50 non reproduite
            if cle in s and not s[cle].get("erreur"):
                continue
            try:
                s[cle] = f(h)
            except Exception as ex:
                s[cle] = {"erreur": str(ex)}
            print(nom, cle, json.dumps(s[cle], ensure_ascii=False)[:160], flush=True)
            fichier.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
            time.sleep(5)
    if "--sans-nu" not in sys.argv:
        for e in ecrans:
            s = res[e["service"]].setdefault("nu", {})
            if e["url"] in s and "erreur" not in s[e["url"]]:
                continue
            try:
                s[e["url"]] = {"gabarit": e["gabarit"], **nu(e["url"])}
            except Exception as ex:
                s[e["url"]] = {"gabarit": e["gabarit"], "erreur": str(ex)}
            print(e["service"], e["gabarit"], "nu", s[e["url"]].get("erreurs", s[e["url"]].get("erreur")), flush=True)
            fichier.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
            time.sleep(20)
    print(fichier)


if __name__ == "__main__":
    main()
