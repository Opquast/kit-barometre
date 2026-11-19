#!/usr/bin/env python3
"""Export CSV détaillé du baromètre des sites : une ligne par règle Opquast et par site.

Pour chaque statut retenu, on garde de quoi le justifier : chaque source et son verdict, le nombre de sources
indépendantes, l'écart entre sources s'il y en a eu et la décision prise (lecture critique), ce qui a déterminé le
statut, et la recommandation. Lit l'état consolidé exactement comme le suivi (scripts/generer_suivi.py) : le CSV et
la page publiée disent donc la même chose.

Sorties (resultats/barometre-AAAA-MM-JJ/) :
- barometre.csv : le détail, une colonne par type d'audit avec son verdict, séparateur « ; », UTF-8 avec BOM (s'ouvre tel
  quel dans Excel) ;
- tests.csv     : tous les tests effectués, une ligne par règle, site et audit : famille et type d'audit, outil, verdict,
  décision retenue, accord ou non avec la décision, et la raison quand l'audit a été contredit ;
- scores.csv    : une ligne par site (score, note, décomptes, part des statuts à deux sources ou plus), avec le score et la
  note du passage précédent et l'écart (vides au premier passage) ;
- changements.csv : une ligne par règle et par site dont le statut retenu a changé depuis le passage précédent (avant,
  après, sens : amélioration, régression ou autre) ; en-tête seul au premier passage.

Le passage précédent est le dossier resultats/barometre-<date> le plus récent strictement antérieur à aujourd'hui.

Usage : python3 scripts/exporter_csv.py
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
import consulter_barometre as cb  # noqa: E402
import generer_suivi as g  # noqa: E402

LIB = {"C": "conforme", "NC": "non conforme", "NA": "non applicable", "NT": "non testé"}
# famille de chaque type d'audit (colonne de la matrice du suivi)
FAMILLE = {"Robot": "Opquast", "Opquast devtools": "Opquast",
           "Réseau": "Scripts maison", "Page": "Scripts maison", "HTML brut": "Scripts maison", "curl": "Scripts maison",
           "Fenêtres": "Scripts maison", "PDF imprimé": "Scripts maison",
           "axe": "Outils libres", "IBM": "Outils libres", "Alfa": "Outils libres", "Sa11y": "Outils libres", "Pa11y": "Outils libres",
           "html-validate": "Outils libres", "Lighthouse": "Outils libres", "Nu": "Outils libres", "REDbot": "Outils libres",
           "i18n": "Outils libres", "SSL Labs": "Outils libres", "Observatory": "Outils libres", "Sitemap": "Outils libres",
           "Relevé": "Lectures avec preuve", "Shopify": "Lectures avec preuve", "Paiement": "Lectures avec preuve",
           "Lecture IA": "Lectures avec preuve", "Captures (IA)": "Lectures avec preuve", "DOM (IA)": "Lectures avec preuve",
           "Contre-ex.": "Humain"}


def par_groupe(srcs: dict) -> dict:
    """Verdict par type d'audit (plusieurs outils de même nature partagent une colonne) : NC l'emporte, puis C, puis NA."""
    out: dict = {}
    for a, x in srcs.items():
        gr = g.ABR.get(a, a)
        if x not in ("C", "NC", "NA"):
            continue
        prev = out.get(gr)
        out[gr] = "NC" if "NC" in (x, prev) else "C" if "C" in (x, prev) else "NA"
    return out


def note(score: float | None) -> str:
    if score is None:
        return "-"
    return "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 65 else "D" if score >= 50 else "E"


def ecrire(chemin: Path, rows: list[dict], champs: list[str] | None = None) -> None:
    with chemin.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=champs or list(rows[0] if rows else {}), delimiter=";")
        w.writeheader()
        # aucun tiret long dans les livrables, même dans un texte cité
        w.writerows([{k: (v.replace(" — ", " - ").replace("—", "-") if isinstance(v, str) else v) for k, v in row.items()} for row in rows])


def comparer(scores: list[dict], lignes: list[dict], jour: str) -> tuple[str | None, list[dict], dict]:
    """Ajoute à scores le score et la note du passage précédent et l'écart ; renvoie (date précédente, changements, sites précédents)."""
    avant = cb.passages(RACINE, avant=jour)
    if not avant:
        for s in scores:
            s.update(score_precedent="", note_precedente="", ecart="")
        return None, [], {}
    dp, dossier = avant[-1]
    prec = {s["site"]: s for s in cb.lire_csv(dossier / "scores.csv")}
    for s in scores:
        p = prec.get(s["site"], {})
        s.update(score_precedent=p.get("score", ""), note_precedente=p.get("note", ""), ecart=cb.ecart(s["score"], p.get("score")))
    chg = [{"date": jour, "date_precedente": dp, **c} for c in cb.changements(cb.lire_csv(dossier / "barometre.csv"), lignes)]
    return dp, chg, prec


def main() -> int:
    g.ETAT.update(g.charger_etat())
    g.charger_annexes()
    lecture = g.LECTURE
    ref = {str(r["number"]): r for r in json.loads((RACINE / "referentiel" / "opquast-checklist-v5.json").read_text(encoding="utf-8"))}
    volet = {r["numero"]: r["methode"] for r in csv.DictReader((RACINE / "referentiel" / "repartition-regles.csv").open(encoding="utf-8"))}
    sortie = RACINE / "resultats" / f"barometre-{date.today():%Y-%m-%d}"
    sortie.mkdir(parents=True, exist_ok=True)
    lignes, scores, tests = [], [], []
    colonnes = list(dict.fromkeys(g.ABR.values()))
    for site, regles in g.ETAT.get("sites", {}).items():
        lc = lecture.get(site, {})
        rec, nsrc = lc.get("recoupement", {}), lc.get("sources_par_regle", {})
        ecarts = {e["regle"]: e for e in lc.get("ecarts", [])}
        cpt = Counter()
        deux = 0
        for k in sorted(regles, key=lambda x: int(x) if x.isdigit() else 999):
            r = regles[k]
            st = r["statut"]
            cpt[st] += 1
            srcs = rec.get(k, {})
            groupes = {g.ABR.get(a, a) for a in nsrc.get(k, srcs.keys())}
            deux += len(groupes) >= 2
            e = ecarts.get(k)
            pg = par_groupe(srcs)
            # tous les tests : une ligne par audit (outil réel), avec la décision retenue pour la règle
            for a, x in sorted(srcs.items()):
                if x not in ("C", "NC", "NA"):
                    continue
                gr = g.ABR.get(a, a)
                tests.append({"date": f"{date.today():%Y-%m-%d}", "site": site, "regle": int(k),
                              "intitule": ref[k]["description"]["fr"] if k in ref else r.get("titre", ""),
                              "volet": volet.get(k, r.get("methode", "")), "famille_audit": FAMILLE.get(gr, "Autre"),
                              "type_audit": gr, "outil": a, "verdict_de_l_audit": LIB.get(x, x),
                              "decision_retenue": LIB.get(st, st),
                              "accord_avec_la_decision": "oui" if x == st else "non" if st in ("C", "NC", "NA") else "-",
                              "ecart_entre_sources": e["type"] if e else "",
                              "raison_de_la_decision": e["pourquoi"] if e and x != st else "",
                              "a_arbitrer": "oui" if e and e.get("a_arbitrer") else ""})
            lignes.append({
                "date": f"{date.today():%Y-%m-%d}", "site": site, "regle": int(k),
                "theme": ", ".join(ref[k]["metadata"].get("Thématiques", [])) if k in ref else r.get("theme", ""),
                "intitule": ref[k]["description"]["fr"] if k in ref else r.get("titre", ""),
                "volet": volet.get(k, r.get("methode", "")),
                "statut_retenu": LIB.get(st, st),
                "nb_sources": len(groupes),
                **{f"audit {c}": LIB.get(pg[c], "") if c in pg else "" for c in colonnes},
                "sources_et_verdicts": " | ".join(f"{a} = {LIB.get(x, x)}" for a, x in sorted(srcs.items())),
                "ecart_entre_sources": e["type"] if e else "",
                "decision_et_raison": (e["pourquoi"] if e else ""),
                "a_arbitrer": "oui" if e and e.get("a_arbitrer") else "",
                "determinant": " / ".join(r.get("determinant", [])[:2])[:600],
                "recommandation": r.get("recommandation", "") if st == "NC" else "",
                "audit_esm": " ; ".join(x["url"] for x in r.get("sources", []) if x.get("url"))[:300],
            })
        tranchees = cpt["C"] + cpt["NC"]
        sc = round(100 * cpt["C"] / tranchees) if tranchees else None
        scores.append({"site": site, "score": sc, "note": note(sc), "conformes": cpt["C"], "non_conformes": cpt["NC"],
                       "non_applicables": cpt["NA"], "non_testees": cpt["NT"], "regles_mesurees": len(regles),
                       "part_deux_sources_ou_plus": f"{round(100 * deux / max(1, len(regles)))} %"})
    jour = f"{date.today():%Y-%m-%d}"
    dp, chg, prec = comparer(scores, lignes, jour)
    for nom, rows in (("barometre.csv", lignes), ("tests.csv", tests), ("scores.csv", scores)):
        ecrire(sortie / nom, rows)
    ecrire(sortie / "changements.csv", chg, cb.CHAMPS_CHANGEMENTS)
    print(f"{len(lignes)} lignes -> {sortie / 'barometre.csv'} ; {len(tests)} tests -> {sortie / 'tests.csv'}")
    for s in scores:
        print(f"  {s['site']} : {s['score']} ({s['note']}), {s['part_deux_sources_ou_plus']} à 2 sources ou plus")
    print(f"Évolution ({len(chg)} changement{'s' * (len(chg) > 1)} -> {sortie / 'changements.csv'}) :" if dp else
          "Évolution : premier passage, rien à comparer")
    for s in scores if dp else []:
        if s["site"] not in prec:
            print(f"  {s['site']} : absent du passage du {dp}, rien à comparer")
            continue
        print(f"  {s['site']} : {s['score_precedent'] or '-'} ({s['note_precedente'] or '-'}) le {dp} -> {'-' if s['score'] is None else s['score']} ({s['note']}), "
              f"écart {s['ecart'] or 'non calculable'} ; {cb.bilan([c for c in chg if c['site'] == s['site']])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
