#!/usr/bin/env python3
"""Compte rendu chiffré du dernier passage, et état du passage avec la prochaine action.

Les chiffres viennent des mêmes fichiers que la page publiée (scores.csv et barometre.csv d'exporter_csv.py, la
dernière lecture critique) : le compte rendu ne peut pas en diverger. Sections : scores et notes par site, part des
statuts à deux sources ou plus, écarts tranchés et à arbitrer, ce qui n'a pas pu être mesuré et pourquoi, ce qui a
changé depuis le passage précédent (si scores.csv porte score_precedent et ecart, ou si changements.csv existe),
puis l'état du passage : étapes faites, lectures IA rendues ou non, prochaine action.

Entrées : resultats/barometre-<date>/{scores,barometre,changements}.csv, resultats/lecture-critique-*/lecture.json,
resultats/etat-passage-*.json (barometre.py), resultats/sources-*/lecture_{ia,visuelle,dom}_lot*.json.
Sortie : resultats/barometre-<date>/compte-rendu.md (la prochaine action est aussi affichée).
Codes de sortie : 0 écrit ; 2 aucun scores.csv (lancer d'abord l'étape synthese).

Usage : python3 scripts/compte_rendu.py [--date AAAA-MM-JJ]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
import ecarts_a_trancher as ea  # noqa: E402
import parc  # noqa: E402

DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")
LECTURES = [("1", "textes légaux", "lecture_ia_lot"), ("2", "captures", "lecture_visuelle_lot"), ("3", "DOM, captures et paiement", "lecture_dom_lot")]
AUTOMATIQUES = ("mesure", "releve", "sources")
SANS_RAISON = "aucune source n'a tranché"


def lire_csv(f: Path) -> list[dict]:
    if not f.is_file():
        return []
    with f.open(encoding="utf-8-sig", newline="") as h:
        return list(csv.DictReader(h, delimiter=";"))


def date_de(p: Path) -> str:
    m = DATE.search(p.name)
    return m.group(1) if m else ""


def etat_passage(jusqua: str) -> dict:
    """Dernier état de passage écrit par barometre.py, au plus tard à la date du compte rendu."""
    l = [f for f in sorted(RACINE.glob("resultats/etat-passage-*.json")) if date_de(f) <= jusqua]
    return json.loads(l[-1].read_text(encoding="utf-8")) if l else {}


def lectures_rendues(depuis: str) -> dict[str, list[Path]]:
    """Fichiers de chaque lecture IA (1, 2, 3) déposés dans resultats/sources-<date>/ depuis le début du passage."""
    out = {}
    for n, _, prefixe in LECTURES:
        out[n] = [f for f in sorted(RACINE.glob(f"resultats/sources-*/{prefixe}*.json")) if date_de(f.parent) >= depuis]
    return out


def tableau(entetes: list[str], lignes: list[list]) -> list[str]:
    return ["| " + " | ".join(entetes) + " |", "|" + "---|" * len(entetes)] + ["| " + " | ".join(str(x) for x in l) + " |" for l in lignes]


def section_changements(scores: list[dict], changements: list[dict]) -> list[str]:
    out = []
    if scores and "score_precedent" in scores[0]:
        out += ["Scores par rapport au passage précédent :", ""]
        out += tableau(["Site", "Avant", "Maintenant", "Écart"],
                       [[s["site"], f"{s['score_precedent'] or '-'} ({s.get('note_precedente') or '-'})", f"{s['score']} ({s['note']})",
                         s.get("ecart") or "-"] for s in scores])
        out.append("")
    if changements:
        par_sens = Counter(c.get("sens", "autre") for c in changements)
        out.append(f"Règles qui ont changé de statut : {len(changements)} ({par_sens['amélioration']} amélioration(s), "
                   f"{par_sens['régression']} régression(s), {par_sens['autre']} autre(s)).")
        for sens, titre in (("régression", "De conforme à non conforme"), ("amélioration", "De non conforme à conforme")):
            l = [c for c in changements if c.get("sens") == sens]
            if l:
                out += ["", f"{titre} :"] + [f"- {c['site']}, règle {c['regle']} : {c.get('intitule', '')}" for c in l]
        out.append("")
    elif out:
        out += ["Aucune règle n'a changé de statut (ou pas de passage précédent comparable).", ""]
    return out


def prochaine_action(etat: dict, lectures: dict, synthese_a_jour: bool, sans: int, arb: int, qui: str) -> str:
    if etat.get("echecs"):
        return f"Reprendre l'étape en échec : {etat['reprise']}"
    if etat and not etat.get("termine"):
        return "Attendre la fin du passage en cours (python3 scripts/bilan_journal.py pour voir où il en est)."
    if not lectures["1"] or not lectures["2"]:
        return ("Lancer les lectures IA 1 (textes légaux) et 2 (captures) décrites dans references/lectures-independantes.md, "
                "puis python3 scripts/barometre.py --hors <hors> --etapes synthese.")
    if not synthese_a_jour:
        return "Des lectures sont plus récentes que la synthèse : relancer python3 scripts/barometre.py --hors <hors> --etapes synthese."
    if not lectures["3"]:
        return "Lancer la lecture 3 sur <hors>/regles_une_source.json, puis relancer --etapes synthese."
    if sans:
        return f"Trancher les {sans} écart(s) sans décision : python3 scripts/ecarts_a_trancher.py --dossier."
    if arb:
        return f"Présenter à {qui} les {arb} écart(s) à arbitrer (python3 scripts/ecarts_a_trancher.py --dossier), puis publier."
    return "Publier : python3 scripts/verifier_publication.py à 0, page Artifact, CSV, eServices Manager, commit."


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date", help="date du dossier resultats/barometre-<date> (défaut : le dernier)")
    a = ap.parse_args(argv)
    dossiers = sorted(d for d in RACINE.glob("resultats/barometre-*") if (d / "scores.csv").is_file() and (not a.date or d.name.endswith(a.date)))
    if not dossiers:
        print("Aucun scores.csv (resultats/barometre-<date>/) : lancer d'abord l'étape synthese.", file=sys.stderr)
        return 2
    dossier = dossiers[-1]
    jour = date_de(dossier)
    scores, detail = lire_csv(dossier / "scores.csv"), lire_csv(dossier / "barometre.csv")
    qui = parc.responsable(RACINE)
    chemin_lc, lecture = ea.charger(None)
    sans, arb = ea.ecarts(lecture)
    etat = etat_passage(jour)
    debut = etat.get("date", jour)
    lectures = lectures_rendues(debut)
    synthese_a_jour = bool(chemin_lc) and all(f.stat().st_mtime <= chemin_lc.stat().st_mtime for l in lectures.values() for f in l)

    md = [f"# Compte rendu du baromètre, passage du {debut}", "",
          f"Chiffres tirés de `resultats/{dossier.name}/scores.csv` et de la dernière lecture critique : ce sont ceux de la page publiée.", "",
          "## Scores et notes par site", ""]
    md += tableau(["Site", "Score", "Note", "Conformes", "Non conformes", "Non applicables", "Non testées", "Règles mesurées"],
                  [[s["site"], s["score"] or "-", s["note"], s["conformes"], s["non_conformes"], s["non_applicables"], s["non_testees"],
                    s["regles_mesurees"]] for s in scores])
    md += ["", "## Part des statuts à deux sources ou plus", ""]
    md += [f"- {s['site']} : {s['part_deux_sources_ou_plus']}" for s in scores]
    if detail:
        deux = sum(1 for r in detail if r.get("nb_sources", "0").isdigit() and int(r["nb_sources"]) >= 2)
        md.append(f"- Ensemble du parc : {round(100 * deux / len(detail))} % ({deux} statuts sur {len(detail)})")

    md += ["", "## Écarts entre sources", ""]
    tranches = [(s, e) for s, v in lecture.items() if not s.startswith("_") for e in v.get("ecarts", [])
                if e.get("regle") != "-" and e.get("statut") in ea.DECIDES]
    par_site = Counter(s for s, _ in tranches)
    md.append(f"Écarts tranchés : {len(tranches)}" + (" (" + ", ".join(f"{s} {n}" for s, n in par_site.items()) + ")" if par_site else "") + ".")
    md.append(f"Écarts à arbitrer par {qui} : {len(arb)}.")
    md += [f"- {s}, règle {e['regle']} ({ea.LIB.get(e['statut'], e['statut'])} retenu) : {e.get('titre', '')}" for s, e, _ in arb]
    md.append(f"Écarts sans décision : {len(sans)}." + (" Voir python3 scripts/ecarts_a_trancher.py --dossier." if sans else ""))
    if not chemin_lc:
        md.append("Aucune lecture critique trouvée : les écarts n'ont pas été recoupés.")

    md += ["", "## Ce qui n'a pas pu être mesuré", ""]
    nt = [r for r in detail if r.get("statut_retenu") == "non testé"]
    for s in scores:
        l = [r for r in nt if r["site"] == s["site"]]
        if l:
            md.append(f"- {s['site']} : {len(l)} règle(s) non testée(s)")
            md += [f"  - règle {r['regle']} : {(r.get('decision_et_raison') or r.get('determinant') or SANS_RAISON).strip()[:200]}" for r in l]
    if not nt:
        md.append("- Aucune règle mesurée n'est restée non testée." if detail else "- Détail par règle absent (barometre.csv) : voir scores.csv, colonne non_testees.")
    md += [f"- Commande en échec ({x['etape']}) : `{x['commande']}`, code {x['code']}." for x in etat.get("echecs", [])]
    if not list(RACINE.glob("resultats/esm-basics-*")):
        md.append("- Robot Opquast basics d'eServices Manager : aucun export, ses verdicts sont absents.")
    md += [f"- Lecture {n} ({nom}) non rendue." for n, nom, _ in LECTURES if not lectures[n]]

    changement = section_changements(scores, lire_csv(dossier / "changements.csv"))
    if changement:
        md += ["", "## Ce qui a changé", ""] + changement[:-1]

    md += ["", "## État du passage", ""]
    if etat:
        faites = [e for e, v in etat["etapes"].items() if v["statut"] == "fait"]
        autres = [f"{e} ({v['statut']})" for e, v in etat["etapes"].items() if v["statut"] != "fait"]
        md.append(f"- Étapes faites : {', '.join(faites) or 'aucune'}" + (f" ; autres : {', '.join(autres)}" if autres else "") + ".")
        manquantes = [e for e in AUTOMATIQUES if e not in etat["etapes"]]
        if manquantes:
            md.append(f"- Étapes non lancées dans ce passage : {', '.join(manquantes)} (résultats d'un passage antérieur).")
    else:
        md.append("- Aucun état de passage (resultats/etat-passage-*.json) : étapes inconnues.")
    for n, nom, _ in LECTURES:
        md.append(f"- Lecture {n} ({nom}) : " + (f"rendue ({len(lectures[n])} fichier(s))" if lectures[n] else "non rendue"))
    md.append(f"- Synthèse : {'à jour des lectures' if synthese_a_jour else 'antérieure à des lectures rendues, ou absente'}.")
    action = prochaine_action(etat, lectures, synthese_a_jour, len(sans), len(arb), qui)
    md += [f"- Prochaine action : {action}", ""]

    sortie = dossier / "compte-rendu.md"
    sortie.write_text("\n".join(md), encoding="utf-8")
    print(f"{sortie}\nProchaine action : {action}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
