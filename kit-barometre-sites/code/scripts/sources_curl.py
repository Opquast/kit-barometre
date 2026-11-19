#!/usr/bin/env python3
"""Deuxième mesure réseau avec curl (autre client HTTP que scripts/controles_reseau.py, qui utilise http.client).

Règles : 25 (politique de referrer), 135 (langue préférée), 207 (type MIME des ressources), 209 (listage de
répertoires), 210 (protection XSS), 213 (logiciels annoncés par le serveur), 218 (avec et sans www), 221 (pas de
redirection forcée vers le mobile). Lecture seule, requêtes espacées.

Usage : python3 scripts/sources_curl.py
Sortie : resultats/sources-AAAA-MM-JJ/curl.json  { site: { regle: [statut, preuve, "curl"] } }
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlsplit

RACINE = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
MOBILE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"


def curl(url: str, *opts: str) -> tuple[dict, str, str, int]:
    """Renvoie (en-têtes de la dernière réponse, corps, URL finale, code)."""
    time.sleep(4)
    p = subprocess.run(["curl", "-sS", "-L", "--max-time", "30", "--compressed", "-A", UA, "-H", "Accept-Language: fr-FR,fr;q=0.9",
                        "-D", "-", "-w", "\n__FIN__%{url_effective} %{http_code}", *opts, url], capture_output=True, text=True, errors="replace")
    sortie = p.stdout
    corps, _, fin = sortie.rpartition("\n__FIN__")
    finale, _, code = fin.partition(" ")
    blocs = re.split(r"\r?\n\r?\n", corps)
    ent, i = {}, 0
    # derniers en-têtes HTTP de la chaîne de redirections
    tetes = [b for b in blocs if b.startswith("HTTP/")]
    if tetes:
        for l in tetes[-1].splitlines()[1:]:
            k, _, v = l.partition(":")
            ent[k.strip().lower()] = v.strip()
        i = corps.find(tetes[-1]) + len(tetes[-1])
    return ent, corps[i:], finale, int(code or 0)


def main() -> None:
    ecrans = list(csv.DictReader((RACINE / "scripts" / "ecrans_en_ligne.csv").open(encoding="utf-8")))
    res: dict = {}
    for nom in dict.fromkeys(e["service"] for e in ecrans):
        acc = next(e["url"] for e in ecrans if e["service"] == nom)
        hote = urlsplit(acc).netloc
        r: dict = {}
        def mis(n, st, preuve): r[str(n)] = [st, preuve[:220], "curl"]
        ent, corps, finale, code = curl(acc)
        meta = re.search(r'<meta[^>]+name=["\']referrer["\'][^>]*content=["\']([^"\']+)', corps, re.I)
        rp = ent.get("referrer-policy") or (meta.group(1) + " (meta)" if meta else "")
        mis(25, "C" if rp else "NC", f"Referrer-Policy : {rp or 'absente'}")
        mis(210, "C" if ent.get("x-xss-protection") or ent.get("content-security-policy") else "NC",
            f"X-XSS-Protection : {ent.get('x-xss-protection', 'absent')} ; CSP : {'présente' if ent.get('content-security-policy') else 'absente'}")
        bavard = {k: v for k, v in ent.items() if k in ("server", "x-powered-by", "x-aspnet-version", "x-generator") and re.search(r"\d|php|apache|nginx|express|asp", v, re.I)}
        mis(213, "NC" if bavard else "C", "logiciel annoncé : " + ", ".join(f"{k}: {v}" for k, v in bavard.items()) if bavard else f"Server : {ent.get('server', 'absent')} (aucune version de logiciel)")
        # 207 : type MIME sur la page et sur 6 ressources
        ress = re.findall(r'(?:src|href)=["\']((?:https?:)?//[^"\']+\.(?:css|js|png|jpg|jpeg|webp|svg|woff2)(?:\?[^"\']*)?)["\']', corps, re.I)[:6]
        sans = []
        if not ent.get("content-type"):
            sans.append("page HTML")
        for u in ress:
            e2, _, _, c2 = curl(urljoin(acc, u), "-I")
            if c2 and not e2.get("content-type"):
                sans.append(u.split("/")[-1][:30])
        mis(207, "NC" if sans else "C", f"type MIME absent sur : {', '.join(sans)}" if sans else f"type MIME présent sur la page et sur {len(ress)} ressource(s)")
        # 218 : avec et sans www
        autre = hote[4:] if hote.startswith("www.") else "www." + hote
        _, _, f2, c2 = curl(f"https://{autre}/", "-I")
        mis(218, "C" if c2 and c2 < 400 else "NC", f"https://{autre}/ : code {c2}, aboutit à {f2[:60]}")
        # 221 : mobile
        _, _, fm, cm = curl(acc, "-I", "-A", MOBILE)
        mis(221, "C" if urlsplit(fm).netloc == urlsplit(finale).netloc and urlsplit(fm).path.rstrip("/") == urlsplit(finale).path.rstrip("/") else "NC",
            f"mobile : {fm[:70]} ; ordinateur : {finale[:70]}")
        # 135 : langue préférée
        lang = {l.split("-")[0].lower() for l in re.findall(r'<link[^>]+hreflang=["\']([a-zA-Z-]+)', corps, re.I) if l.lower() != "x-default"}
        if len(lang) < 2:
            mis(135, "NA", "une seule langue proposée (aucune alternative hreflang)")
        else:
            cible = next(l for l in sorted(lang) if l != "fr")
            _, c3, f3, _ = curl(acc, "-H", f"Accept-Language: {cible};q=1.0,fr;q=0.1")
            h = re.search(r'<html[^>]+lang=["\']([a-zA-Z-]+)', c3, re.I)
            mis(135, "C" if h and h.group(1).split("-")[0].lower() == cible else "NC", f"préférence « {cible} » : page servie en « {h.group(1) if h else '?'} » ({f3[:60]})")
        # 209 : listage de répertoires
        listes = []
        for d in ("/cdn/shop/", "/assets/", "/files/"):
            _, c4, _, k4 = curl(f"https://{hote}{d}")
            if k4 == 200 and re.search(r"<title>\s*Index of|Parent Directory", c4[:20000], re.I):
                listes.append(d)
        mis(209, "NC" if listes else "C", f"listage affiché : {', '.join(listes)}" if listes else "aucun listage sur /cdn/shop/, /assets/ et /files/")
        res[nom] = r
        print(nom, {k: v[0] for k, v in r.items()}, flush=True)
    d = RACINE / "resultats" / f"sources-{date.today():%Y-%m-%d}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "curl.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
