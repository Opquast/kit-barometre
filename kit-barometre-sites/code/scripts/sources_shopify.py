#!/usr/bin/env python3
"""Deuxièmes sources tirées des données publiques de Shopify (lecture seule, requêtes GET espacées).

Logique indépendante du relevé navigateur (scripts/releve_regles.mjs) : on ne lit pas l'affichage de la page dans
Chromium, mais les données que Shopify publie pour les machines :
- /meta.json : pays livrés, pays de la boutique ;
- /products/<handle>.js (API Ajax documentée) : disponibilité des variantes ;
- données structurées JSON-LD (schema.org) du HTML brut de la fiche produit et de l'article : Offer.availability,
  datePublished, dateModified ;
- /blogs/<handle>.atom : flux des nouveaux contenus ;
- /policies/<handle>.json : textes des politiques (conservés HORS du dépôt, comme les textes du relevé, pour la
  lecture indépendante) ;
- HTML brut d'une adresse inexistante : page 404 personnalisée et menu présent (sans exécuter de JavaScript).

Règles tranchées : 1, 34, 47, 129 (pays des adresses), 223, 225, 231. Les textes des politiques servent à la lecture
indépendante des règles de contenu (scripts/lecture_independante, résultats dans resultats/sources-*/lecture_ia.json).

Usage : python3 scripts/sources_shopify.py <dossier hors dépôt pour les textes> [--delai 8]
Sortie : resultats/sources-AAAA-MM-JJ/shopify.json  { site: { regle: [statut, preuve, outil] } }
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import secrets
import sys
import time
from datetime import date
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

RACINE = Path(__file__).resolve().parent.parent
UA = "Opquast-barometre-Colorz/0.3.0 (sources publiques Shopify, lecture seule)"
POLITIQUES = ["privacy-policy", "refund-policy", "shipping-policy", "terms-of-service", "terms-of-sale", "legal-notice", "contact-information"]
PAYS = r"\b(France|FRANCE|Belgique|Suisse|Luxembourg|Espagne|Italie|Allemagne|Portugal|Royaume-Uni|Pays-Bas)\b"
DELAI = 8.0


def get(url: str) -> tuple[int, str, str]:
    time.sleep(DELAI)
    for essai in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"}), timeout=25) as r:  # nosec B310: URL http(s) du parc ou d'un service connu
                return r.status, r.geturl(), r.read().decode("utf-8", "replace")
        except HTTPError as e:
            if e.code == 429 and essai < 2:
                time.sleep(30 * (essai + 1))
                continue
            return e.code, url, e.read().decode("utf-8", "replace") if e.fp else ""
        except (URLError, TimeoutError, OSError) as e:
            return 0, url, str(e)
    return 429, url, ""  # pragma: no cover  (inaccessible : le 3e essai renvoie toujours)


def jsonld(html: str) -> list:
    out = []
    for bloc in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            d = json.loads(bloc.strip())
        except json.JSONDecodeError:
            continue
        pile = d if isinstance(d, list) else [d]
        while pile:
            x = pile.pop()
            if isinstance(x, dict):
                out.append(x)
                pile += [v for v in x.values() if isinstance(v, (dict, list))]
            elif isinstance(x, list):
                pile += x
    return out


def texte(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html))).strip()


def main() -> int:
    global DELAI
    ap = argparse.ArgumentParser()
    ap.add_argument("textes")
    ap.add_argument("--delai", type=float, default=8.0)
    a = ap.parse_args()
    DELAI = a.delai
    dossier_textes = Path(a.textes)
    dossier_textes.mkdir(parents=True, exist_ok=True)
    ecrans = list(csv.DictReader((RACINE / "scripts" / "ecrans_en_ligne.csv").open(encoding="utf-8")))
    sortie = RACINE / "resultats" / f"sources-{date.today():%Y-%m-%d}"
    sortie.mkdir(parents=True, exist_ok=True)
    f = sortie / "shopify.json"
    res = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    for nom in dict.fromkeys(e["service"] for e in ecrans):
        if res.get(nom, {}).get("_fini"):
            continue
        ec = [e for e in ecrans if e["service"] == nom]
        accueil = ec[0]["url"].rstrip("/")
        base = re.match(r"https?://[^/]+", accueil).group(0)
        prefixe_langue = accueil[len(base):]  # /fr chez Boutique D
        r: dict = {}
        print("==", nom, flush=True)

        st, _, corps = get(f"{base}/meta.json")
        meta = json.loads(corps) if st == 200 and corps.startswith("{") else {}
        if st in (403, 503) or "challenge" in corps[:3000].lower():
            r["_limite"] = f"meta.json : code {st}, vérification anti-robot possible : le site est laissé de côté"
            res[nom] = r
            continue
        pays = meta.get("ships_to_countries") or []
        r["47"] = ["C" if pays else "I", f"/meta.json : livraison vers {len(pays)} pays ({', '.join(pays[:8])}{'…' if len(pays) > 8 else ''})" if pays else "/meta.json sans liste de pays livrés", "Shopify meta.json"]

        prod = next((e["url"] for e in ec if e["gabarit"] == "Produit"), None)
        if prod:
            st, _, corps = get(prod.split("?")[0] + ".js")
            if st == 200 and corps.startswith("{"):
                p = json.loads(corps)
                v = p.get("variants", [])
                r["_produit"] = {"disponible": p.get("available"), "variantes": len(v), "indisponibles": sum(1 for x in v if not x.get("available"))}
            st, _, html = get(prod)
            offres = [x for x in jsonld(html) if x.get("@type") in ("Offer", "AggregateOffer") or "availability" in x]
            dispo = sorted({str(x.get("availability", "")).rsplit("/", 1)[-1] for x in offres if x.get("availability")})
            r["34"] = ["C" if dispo else "I", f"JSON-LD de la fiche produit : availability = {', '.join(dispo)}" if dispo else "Aucune disponibilité dans les données structurées de la fiche produit (l'affichage n'est pas jugé ici)", "Shopify JSON-LD et API Ajax"]

        # 231 : date programmatique sur un article de blog (écran de type article ou recette)
        art = next((e["url"] for e in ec if "blogs/" in e["url"]), None)
        if art:
            st, _, html = get(art)
            d = [x for x in jsonld(html) if x.get("datePublished") or x.get("dateModified")]
            t = re.search(r'<time[^>]+datetime=["\']([^"\']+)', html)
            m = re.search(r'<meta[^>]+property=["\']article:(published|modified)_time["\'][^>]+content=["\']([^"\']+)', html)
            ok = d or t or m
            r["231"] = ["C" if ok else "NC", "HTML brut de l'article : " + ", ".join(x for x in [
                f"JSON-LD datePublished {d[0].get('datePublished', '')}" if d else "", f"<time datetime={t.group(1)}>" if t else "",
                f"meta article:{m.group(1)}_time" if m else ""] if x) if ok else "HTML brut de l'article : aucune date lisible par les machines (JSON-LD, time, meta)", "HTML brut et JSON-LD"]

        # 1 : flux Atom des nouveaux contenus
        st, _, html_acc = get(accueil if accueil.endswith("/") or prefixe_langue else accueil + "/")
        blogs = sorted(set(re.findall(r'href="(?:https?://[^/"]+)?((?:/[a-z]{2})?/blogs/[a-z0-9-]+)/?"', html_acc)))
        flux = [l for l in re.findall(r'<link[^>]+type=["\']application/(?:atom|rss)\+xml["\'][^>]*>', html_acc)]
        if not flux and blogs:
            st, _, corps = get(base + blogs[0] + ".atom")
            if st == 200 and "<feed" in corps[:500]:
                flux = [f"{blogs[0]}.atom ({corps.count('<entry')} entrées)"]
        r["1"] = ["C" if flux else "I", ("Flux des nouveaux contenus : " + "; ".join(x[:90] for x in flux[:2])) if flux else "Aucun flux Atom ou RSS (les nouveautés peuvent être signalées autrement)", "HTML brut et flux Atom Shopify"]

        # 223 et 225 : page 404 en HTML brut, sans JavaScript
        st, _, html = get(f"{base}{prefixe_langue}/controle-opquast-{secrets.token_hex(4)}")
        nav_acc = set(re.findall(r'<a[^>]+href="((?:/[a-z]{2})?/(?:collections|pages)/[^"#?]+)"', html_acc))
        nav_404 = set(re.findall(r'<a[^>]+href="((?:/[a-z]{2})?/(?:collections|pages)/[^"#?]+)"', html))
        perso = st == 404 and len(html) > 5000 and bool(re.search(r"<header|<nav", html, re.I))
        r["223"] = ["C" if perso else "NC", f"Code {st}, {len(html) // 1024} Ko de HTML, en-tête du site {'présent' if perso else 'absent'}", "HTML brut de la page 404"]
        commun = nav_acc & nav_404
        r["225"] = ["I" if len(nav_acc) < 3 else "C" if len(commun) >= min(3, len(nav_acc)) else "NC", f"{len(commun)} lien(s) du menu de l'accueil présents dans le HTML brut de la 404 (sur {len(nav_acc)})", "HTML brut de la page 404"]

        # politiques : textes conservés hors dépôt pour la lecture indépendante ; 129 tranchée ici
        prefixe = re.sub(r"[^A-Za-z0-9_]+", "_", nom)
        adresses, dispo_pol = [], []
        for h in POLITIQUES:
            st, _, corps = get(f"{base}/policies/{h}.json")
            if st != 200 or not corps.startswith("{"):
                continue
            pol = json.loads(corps).get("policy", {})
            t = texte(pol.get("body", ""))
            if len(t) < 50:
                continue
            dispo_pol.append(h)
            (dossier_textes / f"{prefixe}__politique_{h.replace('-', '_')}.txt").write_text(f"{pol.get('title', h)}\n\n{t}", encoding="utf-8")
            adresses += re.findall(r"[^.;:]{0,80}\b\d{5}\b[^.;:]{0,60}", t)
        r["_politiques"] = dispo_pol
        if adresses:
            avec = [x for x in adresses if re.search(PAYS, x)]
            r["129"] = ["C" if len(avec) == len(adresses) else "NC", f"{len(adresses)} adresse(s) postale(s) dans les politiques Shopify, {len(avec)} avec le pays", "Shopify /policies/*.json"]
        r["_fini"] = True
        res[nom] = r
        f.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(nom, {k: v[0] for k, v in r.items() if not k.startswith("_")}, "politiques :", dispo_pol, flush=True)
    f.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
