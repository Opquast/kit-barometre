#!/usr/bin/env python3
"""Crée, complète ou vérifie le parc mesuré (referentiel/parc.json) à partir des écrans (scripts/ecrans_en_ligne.csv).

Un site par service du CSV, dans l'ordre du CSV. Les valeurs déjà présentes dans parc.json sont gardées ; les champs
manquants prennent une valeur par défaut déduite du nom et des adresses :
- code_esm : WEB-<NOM> (majuscules, sans accents ni espaces), à corriger s'il diffère du code saisi dans eServices Manager ;
- prefixe_pages : initiales du nom (ou ses 4 premières lettres s'il n'a qu'un mot) ;
- plateforme : « shopify » si elle n'est pas connue ;
- compte_client_hors_site : vrai sur Shopify (comptes clients hébergés par shopify.com), faux sinon ;
- prefixe_langue : « /xx » si l'adresse de l'accueil commence par un code de langue, vide sinon ;
- compte_email : vide.
Au niveau du parc : responsable (personne qui valide les décisions) et auditeur_esm (son code court dans ESM).

Vérifications (code de sortie 1 si l'une échoue) : site du CSV absent du parc, site du parc absent du CSV, nom, code
eServices Manager ou préfixe de pages en double. Sans --verifier, le parc est d'abord complété et écrit.

Usage : python3 scripts/configurer_parc.py [--verifier] [--responsable "Prénom Nom"] [--auditeur-esm ABC]
                                          [--parc referentiel/parc.json] [--ecrans scripts/ecrans_en_ligne.csv]
Codes de sortie : 0 parc cohérent, 1 incohérence, 2 fichier des écrans absent ou parc illisible.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import parc

RACINE = Path(__file__).resolve().parent.parent
AIDE = ("Parc mesuré par le baromètre : un objet par site, dans le même ordre que scripts/ecrans_en_ligne.csv. "
        "Généré ou vérifié par scripts/configurer_parc.py. responsable : la personne qui valide les décisions et arbitre "
        "les écarts (affichée dans les rapports) ; auditeur_esm : son code court dans eServices Manager.")


def ascii_majuscules(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().upper()


def code_esm(nom: str) -> str:
    return "WEB-" + (re.sub(r"[^A-Z0-9]", "", ascii_majuscules(nom)) or "SITE")


def prefixe_pages(nom: str) -> str:
    mots = re.findall(r"[A-Z0-9]+", ascii_majuscules(nom))
    if len(mots) > 1:
        return "".join(m[0] for m in mots)
    return mots[0][:4] if mots else "SITE"


def prefixe_langue(url: str) -> str:
    m = re.match(r"/([a-z]{2}(?:-[a-z]{2})?)(?:/|$)", urlsplit(url).path, re.I)
    return f"/{m.group(1).lower()}" if m else ""


def defauts(nom: str, ecrans: list[dict]) -> dict:
    """Valeurs par défaut d'un site, déduites de son nom et de ses écrans."""
    ec = [e for e in ecrans if e["service"] == nom]
    accueil = next((e["url"] for e in ec if e["gabarit"].startswith("Accueil")), ec[0]["url"] if ec else "")
    return {"nom": nom, "code_esm": code_esm(nom), "prefixe_pages": prefixe_pages(nom), "plateforme": "shopify",
            "compte_client_hors_site": True, "prefixe_langue": prefixe_langue(accueil), "compte_email": ""}


def completer(donnees: dict, ecrans: list[dict], responsable: str | None = None, auditeur: str | None = None) -> tuple[dict, list[str]]:
    """Parc complété (sites du CSV ajoutés, champs manquants remplis) et liste des ajouts faits."""
    existants = {s.get("nom"): s for s in donnees.get("sites", [])}
    noms_csv = list(dict.fromkeys(e["service"] for e in ecrans))
    ajouts, sites = [], []
    for nom in noms_csv:
        d = defauts(nom, ecrans)
        s = existants.get(nom)
        if s is None:
            ajouts.append(f"site ajouté : {nom} ({d['code_esm']}, préfixe {d['prefixe_pages']})")
            sites.append(d)
            continue
        manquants = [k for k in parc.CHAMPS if k not in s]
        if "compte_client_hors_site" in manquants:
            d["compte_client_hors_site"] = (s.get("plateforme") or "shopify") == "shopify"
        if manquants:
            ajouts.append(f"{nom} : champs complétés ({', '.join(manquants)})")
        sites.append({**d, **s})
    sites += [s for n, s in existants.items() if n not in noms_csv]  # gardés, signalés par verifier()
    out = {"_aide": donnees.get("_aide", AIDE),
           "responsable": responsable or donnees.get("responsable") or parc.RESPONSABLE_DEFAUT,
           "auditeur_esm": auditeur if auditeur is not None else donnees.get("auditeur_esm", ""),
           **{k: v for k, v in donnees.items() if k not in ("_aide", "responsable", "auditeur_esm", "sites")},
           "sites": sites}
    return out, ajouts


def verifier(donnees: dict, ecrans: list[dict]) -> list[str]:
    """Incohérences entre le parc et le CSV des écrans (liste vide si tout va bien)."""
    sites = donnees.get("sites", [])
    noms_parc = [s.get("nom", "") for s in sites]
    noms_csv = list(dict.fromkeys(e["service"] for e in ecrans))
    pb = [f"site du CSV absent du parc : {n}" for n in noms_csv if n not in noms_parc]
    pb += [f"site du parc absent du CSV : {n}" for n in noms_parc if n not in noms_csv]
    for champ, lib in (("nom", "nom"), ("code_esm", "code eServices Manager"), ("prefixe_pages", "préfixe de pages")):
        compte = Counter(s.get(champ) for s in sites)
        pb += [f"{lib} en double : {v} ({compte[v]} sites)" for v in compte if v and compte[v] > 1]
    pb += [f"{s.get('nom', '?')} : champ manquant {k}" for s in sites for k in parc.CHAMPS if k not in s]
    return pb


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Crée, complète ou vérifie referentiel/parc.json.")
    ap.add_argument("--verifier", action="store_true", help="vérifier seulement, sans rien écrire")
    ap.add_argument("--responsable", help="personne responsable du baromètre")
    ap.add_argument("--auditeur-esm", help="code court de cette personne dans eServices Manager")
    ap.add_argument("--parc", type=Path, help="fichier du parc (par défaut referentiel/parc.json)")
    ap.add_argument("--ecrans", type=Path, help="CSV des écrans (par défaut scripts/ecrans_en_ligne.csv)")
    a = ap.parse_args(argv)
    f_parc = a.parc or RACINE / "referentiel" / "parc.json"
    f_ecrans = a.ecrans or RACINE / "scripts" / "ecrans_en_ligne.csv"
    if not f_ecrans.is_file():
        print(f"Fichier des écrans absent : {f_ecrans}")
        return 2
    ecrans = list(csv.DictReader(f_ecrans.open(encoding="utf-8")))
    try:
        donnees = parc.charger(f_parc) if f_parc.is_file() else {}
    except json.JSONDecodeError as ex:
        print(f"{f_parc} illisible : {ex}")
        return 2
    if not a.verifier:
        donnees, ajouts = completer(donnees, ecrans, a.responsable, a.auditeur_esm)
        f_parc.parent.mkdir(parents=True, exist_ok=True)
        f_parc.write_text(json.dumps(donnees, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{f_parc} : {len(donnees['sites'])} site(s), responsable : {donnees['responsable']}")
        for x in ajouts:
            print("  " + x)
    pb = verifier(donnees, ecrans)
    for x in pb:
        print("INCOHÉRENCE " + x)
    if not pb:
        print(f"Parc cohérent avec {f_ecrans.name} : {len(donnees.get('sites', []))} site(s).")
    return 1 if pb else 0


if __name__ == "__main__":
    sys.exit(main())
