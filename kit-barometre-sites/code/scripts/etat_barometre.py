#!/usr/bin/env python3
"""État consolidé du baromètre : statut de chaque règle, pour chaque service, avec le résultat qui le détermine,
l'audit eServices Manager d'où il vient (nom et lien) et une recommandation propre au site.

Sources :
- sites, sans IA : resultats/esm-scripts-*/<CODE>.json (fusion réseau, code de la page, W3C i18n, REDbot),
  saisis dans les audits « <site>, scripts sans IA » ;
- sites, robot Opquast basics d'eServices Manager : resultats/esm-basics-*/resultats.json (décomptes par page)
  et resultats/esm-basics-*/preuves_nc.json (commentaire du robot pour chaque non-conformité) ;
- e-mails (Klaviyo Boutique C) : resultats/email-*/resultats.csv ;
- identifiants des audits : referentiel/audits-esm.json ; recommandations : referentiel/recommandations.csv.

Statut d'une règle pour un site : non conforme si au moins une page l'est, dans au moins une source ; sinon conforme
si au moins une page l'est ; sinon non applicable ; sinon non testé.

Sortie : resultats/etat-AAAA-MM-JJ/etat.json (lu par scripts/generer_suivi.py).
Usage : python3 scripts/etat_barometre.py
"""
from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SITES = {"WEB-BOUTIQUEA": "Boutique A", "WEB-BOUTIQUEB": "Boutique B", "WEB-BOUTIQUEC": "Boutique C",
         "WEB-BOUTIQUED": "Boutique D", "WEB-BOUTIQUEE": "Boutique E", "WEB-BOUTIQUEF": "Boutique F"}
ORDRE = ["NC", "C", "NA", "NT"]
LIB = {"NC": "non conforme", "C": "conforme", "NA": "non applicable", "NT": "non testé"}


def dernier(motif: str) -> Path | None:
    l = sorted(RACINE.glob(motif))
    return l[-1] if l else None


def lire_json(chemin: Path, defaut):
    """Contenu JSON du fichier, ou la valeur par défaut s'il n'existe pas."""
    return json.loads(chemin.read_text(encoding="utf-8")) if chemin.is_file() else defaut


def combine(statuts: list[str]) -> str:
    for s in ORDRE:
        if s in statuts:
            return s
    return "NT"


def court(t: str, n: int = 260) -> str:
    t = " ".join(t.split())
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def main() -> None:
    reg = {r["number"]: r for r in json.loads((RACINE / "referentiel" / "opquast-checklist-v5.json").read_text(encoding="utf-8"))}
    meth = {int(x["numero"]): x["methode"] for x in csv.DictReader((RACINE / "referentiel" / "repartition-regles.csv").open(encoding="utf-8"))}
    reco = {x["code"]: x["recommandation"] for x in csv.DictReader((RACINE / "referentiel" / "recommandations.csv").open(encoding="utf-8"))}
    audits = json.loads((RACINE / "referentiel" / "audits-esm.json").read_text(encoding="utf-8"))
    lien = lambda typ, site: {"nom": audits["noms"][typ].format(site=site), "url": audits["base"] + audits[typ][site]}
    scripts_dir = dernier("resultats/esm-scripts-*")
    basics_dir = dernier("resultats/esm-basics-*")
    # Sans export eServices Manager (kit neuf ou ESM non utilisé) : sources absentes, colonnes vides, pas d'erreur.
    if basics_dir is None:
        print("Aucun export Opquast basics (resultats/esm-basics-*) : verdicts du robot absents.")
    if scripts_dir is None:
        print("Aucune fusion des scripts (resultats/esm-scripts-*) : lancer d'abord scripts/fusion_scripts.py.")
    basics = lire_json(basics_dir / "resultats.json", {"regles": {}}) if basics_dir else {"regles": {}}
    preuves_robot = lire_json(basics_dir / "preuves_nc.json", {}) if basics_dir else {}
    sites = {}
    for code, nom in SITES.items():
        pages = lire_json(scripts_dir / f"{code}.json", []) if scripts_dir else []
        regles: dict[int, dict] = {}
        for p in pages:
            for n, (st, com) in p["resultats"].items():
                e = regles.setdefault(int(n), {"sc": {}, "robot": None})
                e["sc"].setdefault(st, []).append((p["titre"], com))
        for n, v in basics["regles"].items():
            e = regles.setdefault(int(n), {"sc": {}, "robot": None})
            e["robot"] = {"conforme": "C", "non conforme": "NC", "non applicable": "NA"}.get(v["sites"].get(nom), "NT")
            e["robot_comptes"] = v["comptes_pages"].get(nom, {})
        out = {}
        for n, e in sorted(regles.items()):
            s_scripts = combine(list(e["sc"])) if e["sc"] else None
            final = combine([x for x in (s_scripts, e["robot"]) if x])
            sources, determinant, pages_nc = [], [], []
            if s_scripts:
                sources.append({**lien("scripts", nom), "statut": s_scripts})
            if e["robot"]:
                sources.append({**lien("basics", nom), "statut": e["robot"]})
            if final == "NC":
                if "NC" in e["sc"]:
                    pages_nc += [t for t, _ in e["sc"]["NC"]]
                    t, com = e["sc"]["NC"][0]
                    determinant.append(f"Scripts, {t} : {court(com)}")
                pr = preuves_robot.get(nom, {}).get(str(n))
                if e["robot"] == "NC" and pr:
                    pages_nc += [x for x in pr["pages"] if x not in pages_nc]
                    determinant.append(f"Robot, {pr['pages'][0]} : {court(pr['commentaire'])}")
            elif final in ("C", "NA"):
                if final in e["sc"]:
                    t, com = e["sc"][final][0]
                    nb = len(e["sc"][final])
                    determinant.append(f"Scripts, {nb} page(s) {LIB[final]}s, par exemple {t} : {court(com, 200)}")
                if e["robot"] == final:
                    k = e.get("robot_comptes", {}).get(LIB[final], 0)
                    determinant.append(f"Robot : {LIB[final]} sur {k} page(s) de l'échantillon.")
            else:
                c = e.get("robot_comptes", {})
                raison = (f"robot : {c.get('indéterminé', 0)} page(s) indéterminée(s), {c.get('non testé', 0)} non testée(s)" if c
                          else "aucune page testée (pages refusées par Shopify ou hors du site)")
                determinant.append("Non tranché : " + raison + ".")
            reco_site = ""
            if final == "NC":
                pages_txt = ", ".join(dict.fromkeys(pages_nc))[:200]
                reco_site = f"Sur {nom}" + (f" ({pages_txt})" if pages_txt else "") + " : " + reco.get(str(n), "")
            elif final == "NT" and str(n) in reco:
                reco_site = f"Sur {nom}, à vérifier puis, si besoin : " + reco[str(n)]
            out[str(n)] = {"titre": reg[n]["description"]["fr"], "theme": ", ".join(reg[n]["metadata"].get("Thématiques", [])),
                           "methode": meth.get(n), "statut": final, "scripts": s_scripts, "robot": e["robot"],
                           "pages_nc": list(dict.fromkeys(pages_nc)), "determinant": determinant, "sources": sources,
                           "recommandation": reco_site}
        sites[nom] = out

    emails = {}
    f = dernier("resultats/email-*/resultats.csv")
    if f:
        crit = {x["id"]: x for x in csv.DictReader((RACINE / "referentiel" / "checklist-email.csv").open(encoding="utf-8"))}
        code = {"conforme": "C", "non conforme": "NC", "non applicable": "NA", "non testé": "NT", "indéterminé": "I"}
        compte = "Klaviyo Boutique C"
        for l in csv.DictReader(f.open(encoding="utf-8")):
            e = emails.setdefault(l["critere"], {"titre": crit[l["critere"]]["critere"], "theme": crit[l["critere"]]["theme"], "ecrans": {}})
            e["ecrans"][l["ecran_code"]] = [code.get(l["statut"], l["statut"]), court(f"[{l['methode']}] {l['justification']} {l.get('preuve', '')}", 280)]
        for k, e in emails.items():
            sts = [v[0] for v in e["ecrans"].values()]
            e["statut"] = "NC" if "NC" in sts else "C" if "C" in sts else "I" if "I" in sts else "NA" if "NA" in sts else "NT"
            nc = [c for c, v in e["ecrans"].items() if v[0] == "NC"]
            e["recommandation"] = (f"Sur {compte} ({', '.join(x.replace('BOUTIQUEC-EM-', '').lower() for x in nc)}) : " + reco.get(k, "")) if nc else (
                f"Sur {compte}, à vérifier puis, si besoin : " + reco[k] if e["statut"] in ("I", "NT") and k in reco else "")
            e["source"] = lien("email", compte)
        emails = {compte: emails}
    sortie = RACINE / "resultats" / f"etat-{date.today():%Y-%m-%d}"
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "etat.json").write_text(json.dumps({"date": f"{date.today():%Y-%m-%d}", "sites": sites, "emails": emails},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    nc = sorted({n for s in sites.values() for n, v in s.items() if v["statut"] == "NC"}, key=int)
    manque = [n for n in nc if n not in reco]
    print(f"{sortie}/etat.json : {len(nc)} règles non conformes sur au moins un site ; recommandations manquantes : {manque}")


if __name__ == "__main__":
    main()
