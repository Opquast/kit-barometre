#!/usr/bin/env python3
"""Consultation du baromètre des sites, sans rien relancer : lit les passages déjà faits (resultats/barometre-AAAA-MM-JJ/).

Pour chaque site (ou celui de --site) : la date du dernier passage où il figure, son score et sa note, l'évolution
par rapport au passage précédent (écart de score, règles améliorées, régressées ou autrement changées), puis les règles
non conformes avec leur recommandation. --regle <n> ne montre que cette règle (statut retenu, statut précédent,
recommandation).

Le module sert aussi à scripts/exporter_csv.py, qui s'en sert pour comparer un passage au précédent (passages(),
lire_csv(), changements(), ecart()).

Codes de sortie : 0 si tout va bien ; 1 si aucun passage n'existe ; 2 si le site ou la règle demandés n'existent dans
aucun passage.

Usage : python3 scripts/consulter_barometre.py [--site "Nom du site"] [--regle 12]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
MOTIF = re.compile(r"^barometre-(\d{4}-\d{2}-\d{2})$")
CHAMPS_CHANGEMENTS = ["date", "date_precedente", "site", "regle", "intitule", "avant", "apres", "sens"]


def passages(racine: Path, avant: str | None = None) -> list[tuple[str, Path]]:
    """Passages (date, dossier) contenant un scores.csv, du plus ancien au plus récent ; avant : strictement antérieurs à cette date."""
    res = racine / "resultats"
    if not res.is_dir():
        return []
    out = []
    for d in res.iterdir():
        m = MOTIF.match(d.name)
        if m and (d / "scores.csv").is_file() and (avant is None or m.group(1) < avant):
            out.append((m.group(1), d))
    return sorted(out)


def lire_csv(chemin: Path) -> list[dict]:
    """Lignes d'un CSV du baromètre (« ; », UTF-8 avec BOM) ; liste vide si le fichier manque."""
    if not chemin.is_file():
        return []
    with chemin.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def entier(v) -> int | None:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def ecart(score, precedent) -> str:
    """Écart signé (« +3 », « -2 », « 0 ») ; vide si l'un des deux scores manque."""
    a, b = entier(score), entier(precedent)
    if a is None or b is None:
        return ""
    return f"{a - b:+d}" if a != b else "0"


def sens(avant: str, apres: str) -> str:
    """amélioration : non conforme -> conforme ; régression : conforme -> non conforme ; autre pour tout autre changement."""
    if avant == "non conforme" and apres == "conforme":
        return "amélioration"
    if avant == "conforme" and apres == "non conforme":
        return "régression"
    return "autre"


def changements(precedent: list[dict], courant: list[dict]) -> list[dict]:
    """Règles dont le statut retenu a changé, pour les sites présents dans les deux passages (lignes de barometre.csv).

    Une règle présente d'un seul côté compte comme changée (statut « absente » de l'autre côté).
    """
    def index(rows):
        out: dict = {}
        for r in rows:
            out.setdefault(r["site"], {})[str(r["regle"])] = r
        return out

    p, c = index(precedent), index(courant)
    out = []
    for site in c:
        if site not in p:
            continue
        for k in sorted(set(p[site]) | set(c[site]), key=lambda x: int(x) if x.isdigit() else 10**6):
            a = p[site].get(k, {}).get("statut_retenu", "absente")
            b = c[site].get(k, {}).get("statut_retenu", "absente")
            if a != b:
                intitule = (c[site].get(k) or p[site][k]).get("intitule", "")
                out.append({"site": site, "regle": k, "intitule": intitule, "avant": a, "apres": b, "sens": sens(a, b)})
    return out


def bilan(chg: list[dict]) -> str:
    n = {s: sum(x["sens"] == s for x in chg) for s in ("amélioration", "régression", "autre")}
    return (f"{n['amélioration']} amélioration{'s' * (n['amélioration'] > 1)}, {n['régression']} régression{'s' * (n['régression'] > 1)}, "
            f"{n['autre']} autre{'s' * (n['autre'] > 1)} changement{'s' * (n['autre'] > 1)}")


def historique(racine: Path) -> list[dict]:
    """Chaque passage : date, dossier, scores par site."""
    return [{"date": d, "dossier": p, "scores": {s["site"]: s for s in lire_csv(p / "scores.csv")}} for d, p in passages(racine)]


def afficher_site(site: str, hist: list[dict], regle: str | None) -> bool:
    """Affiche un site ; renvoie False si --regle est demandée et absente du dernier passage du site."""
    avec = [h for h in hist if site in h["scores"]]
    der = avec[-1]
    prec = avec[-2] if len(avec) > 1 else None
    s = der["scores"][site]
    sc = entier(s.get("score"))
    print(f"\n{site} - dernier passage le {der['date']}")
    print(f"  Score : {sc if sc is not None else '-'}/100, note {s.get('note') or '-'}")
    lignes = [r for r in lire_csv(der["dossier"] / "barometre.csv") if r["site"] == site]
    chg: list[dict] = []
    if prec is None:
        print("  Évolution : premier passage pour ce site, rien à comparer")
    else:
        p = prec["scores"][site]
        chg = changements([r for r in lire_csv(prec["dossier"] / "barometre.csv") if r["site"] == site], lignes)
        e = ecart(s.get("score"), p.get("score"))
        print(f"  Évolution depuis le {prec['date']} : {p.get('score') or '-'} ({p.get('note') or '-'}) -> {sc if sc is not None else '-'} "
              f"({s.get('note') or '-'}), écart {e or 'non calculable'} ; {bilan(chg)}")
    if regle is not None:
        r = next((x for x in lignes if str(x["regle"]) == regle), None)
        if r is None:
            print(f"  Règle {regle} : absente de ce passage")
            return False
        c = next((x for x in chg if x["regle"] == regle), None)
        print(f"  Règle {regle} - {r.get('intitule', '')}")
        print(f"    Statut retenu : {r.get('statut_retenu', '')}")
        if prec is not None:
            print(f"    Statut au passage précédent : {c['avant'] if c else r.get('statut_retenu', '')}" + (f" ({c['sens']})" if c else " (inchangé)"))
        if r.get("recommandation"):
            print(f"    Recommandation : {r['recommandation']}")
        return True
    nc = [r for r in lignes if r.get("statut_retenu") == "non conforme"]
    print(f"  Règles non conformes : {len(nc)}")
    for r in nc:
        print(f"    - {r['regle']} {r.get('intitule', '')}" + (f" : {r['recommandation']}" if r.get("recommandation") else ""))
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Consulter le dernier passage du baromètre sans rien relancer.")
    ap.add_argument("--site", help="nom du site (tous par défaut)")
    ap.add_argument("--regle", type=int, help="numéro de règle Opquast à détailler")
    a = ap.parse_args(argv)
    hist = historique(RACINE)
    if not hist:
        print("Aucun passage du baromètre dans resultats/barometre-*/ : lancer d'abord un passage.", file=sys.stderr)
        return 1
    sites = list(dict.fromkeys(s for h in hist for s in h["scores"]))
    if a.site is not None and a.site not in sites:
        print(f"Site inconnu : {a.site}. Sites mesurés : {', '.join(sites)}", file=sys.stderr)
        return 2
    print(f"Baromètre des sites : {len(hist)} passage{'s' * (len(hist) > 1)}, le dernier le {hist[-1]['date']}")
    regle = str(a.regle) if a.regle is not None else None
    trouvee = [afficher_site(s, hist, regle) for s in ([a.site] if a.site else sites)]
    return 0 if any(trouvee) else 2


if __name__ == "__main__":
    sys.exit(main())
