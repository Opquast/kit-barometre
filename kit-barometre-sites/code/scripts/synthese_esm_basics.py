#!/usr/bin/env python3
"""Synthèse des audits « Opquast basics » du robot d'eServices Manager, et comparaison avec nos scripts.

Entrée : resultats/esm-basics-AAAA-MM-JJ/agregat.json (décompte par site et par règle des résultats page par page,
tiré de l'export « Audits » d'eServices Manager ; aucune donnée personnelle).
Sorties dans le même dossier : resultats.json et rapport.md.

Statut d'une règle pour un site : non conforme si au moins une page l'est ; sinon conforme si au moins une page l'est ;
sinon indéterminé, non applicable ou non testé.

Usage : python3 scripts/synthese_esm_basics.py resultats/esm-basics-2026-11-12
"""
from __future__ import annotations

import csv
import difflib
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
ANALYSE = """## Pourquoi le robot et le script divergent

Les 16 écarts portent sur 3 règles et viennent du niveau d'exigence, pas des faits : les deux outils relèvent les mêmes en-têtes.

- **199, HSTS** : l'en-tête est présent sur les six sites avec `max-age=7889238` (91 jours). Le script le juge conforme (en-tête présent) ; le robot demande au moins un an, avec `includeSubDomains` et `preload`.
- **217, domaine de messagerie authentifié** : SPF et DMARC existent partout. Le robot refuse une politique DMARC `p=none` (surveillance seule, aucun e-mail usurpé bloqué) : Boutique B, Boutique D, Boutique E et Boutique F. Le script ne vérifiait que la présence.
- **227, mise en cache** : la page HTML est servie en `private, max-age=0, must-revalidate`, les fichiers statiques du CDN Shopify sont bien mis en cache. Le script se contente d'en-têtes de cache présents ; le robot exige que la page elle-même soit mise en cache.

Le robot applique un seuil que la règle Opquast n'écrit pas ; le script, lui, est plus indulgent. C'est l'incertitude de mesure à documenter : on retient pour le baromètre le verdict le plus exigeant quand les faits sont établis (199 et 217), et on note 227 comme discutable sur Shopify (le HTML dynamique n'a pas vocation à être mis en cache).
"""
STATUTS = ["conforme", "non conforme", "indéterminé", "non applicable", "non testé"]


def statut_site(c: list[int]) -> str:
    if c[1]:
        return "non conforme"
    if c[0]:
        return "conforme"
    for i in (2, 3, 4):
        if c[i]:
            return STATUTS[i]
    return "non testé"


def numeros(intitules: list[str]) -> list[int]:
    regles = json.loads((RACINE / "referentiel" / "opquast-checklist-v5.json").read_text(encoding="utf-8"))
    par_texte = {r["description"]["fr"].replace("’", "'"): r["number"] for r in regles}
    out = []
    for t in intitules:
        m = difflib.get_close_matches(t.replace("’", "'"), par_texte, 1, 0.8)
        if not m:
            raise SystemExit(f"Intitulé introuvable dans le référentiel : {t}")
        out.append(par_texte[m[0]])
    return out


def reseau() -> dict[str, dict[int, str]]:
    """Statut par site et par règle de nos contrôles réseau (dernier passage de chaque site)."""
    res: dict[str, dict[int, str]] = {}
    for f in sorted((RACINE / "resultats").glob("reseau-*/resultats.json")):
        for site, v in json.loads(f.read_text(encoding="utf-8"))["services"].items():
            st: dict[int, list[str]] = {}
            for c in v.get("site", []):
                st.setdefault(c["rule_number"], []).append(c["status"].replace("-", " "))
            for p in v.get("pages", []):
                for c in p.get("controles", []):
                    st.setdefault(c["rule_number"], []).append(c["status"].replace("-", " "))
            res[site] = {n: ("non conforme" if "non conforme" in s else "conforme" if "conforme" in s else s[0]) for n, s in st.items()}
    return res


def main() -> None:
    dossier = Path(sys.argv[1] if len(sys.argv) > 1 else "resultats/esm-basics-2026-11-12")
    a = json.loads((dossier / "agregat.json").read_text(encoding="utf-8"))
    nums = numeros(a["intitules"])
    meth = {int(x["numero"]): x["methode"] for x in csv.DictReader((RACINE / "referentiel" / "repartition-regles.csv").open(encoding="utf-8"))}
    net = reseau()
    sites = list(a["comptes"])
    tab = {s: {n: statut_site(c) for n, c in zip(nums, a["comptes"][s])} for s in sites}

    md = [f"# Audits « Opquast basics » du robot d'eServices Manager ({a['date']})", "",
          "65 règles du socle Opquast, audit automatique du robot sur les pages de chaque service (7 pour Boutique A, 8 pour les autres).",
          "Statut d'une règle pour un site : non conforme si au moins une page l'est. Source : export « Audits » d'eServices Manager.", "",
          "## Synthèse par site", "", "| Site | Score ESM | Conformes | Non conformes | Indéterminées | Non applicables | Non testées |", "|---|---|---|---|---|---|---|"]
    for s in sites:
        n = [list(tab[s].values()).count(x) for x in STATUTS]
        md.append(f"| {s} | {a['scores'][s]} % | " + " | ".join(map(str, n)) + " |")
    md += ["", "Le score d'eServices Manager compte les résultats page par page ; les colonnes suivantes comptent les règles au niveau du site.", ""]

    nc_partout = [n for n in nums if all(tab[s][n] == "non conforme" for s in sites)]
    md += ["## Règles non conformes sur les six sites", ""]
    titre = dict(zip(nums, a["intitules"]))
    md += [f"- **{n}** : {titre[n]} (méthode chez nous : {meth.get(n, '?')})" for n in sorted(nc_partout)] + [""]

    md += ["## Robot et script réseau sur les règles communes", "",
           "| Règle | " + " | ".join(sites) + " |", "|---|" + "---|" * len(sites)]
    accord = desaccord = 0
    ecarts = []
    for n in sorted(nums):
        if not any(n in net.get(s, {}) for s in sites):
            continue
        cells = []
        for s in sites:
            r, m = tab[s][n], net.get(s, {}).get(n)
            if m is None or r not in ("conforme", "non conforme") or m not in ("conforme", "non conforme"):
                cells.append(f"robot {r} / script {m or '—'}")
                continue
            if r == m:
                accord += 1
                cells.append(f"accord ({r})")
            else:
                desaccord += 1
                ecarts.append((n, s, r, m))
                cells.append(f"**écart** : robot {r}, script {m}")
        md.append(f"| {n} | " + " | ".join(cells) + " |")
    md += ["", f"**Bilan** : {accord} verdicts identiques, {desaccord} écarts entre le robot et le script réseau.", ""]
    md.append(ANALYSE)

    out = {"date": a["date"], "checklist": a["checklist"], "scores": a["scores"],
           "regles": {str(n): {"intitule": titre[n], "methode_chez_nous": meth.get(n), "sites": {s: tab[s][n] for s in sites},
                                "comptes_pages": {s: dict(zip(STATUTS, a["comptes"][s][nums.index(n)])) for s in sites}} for n in sorted(nums)},
           "comparaison_reseau": {"accords": accord, "ecarts": [{"regle": n, "site": s, "robot": r, "script": m} for n, s, r, m in ecarts]}}
    (dossier / "resultats.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    (dossier / "rapport.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"{dossier}/rapport.md : {len(sites)} sites, {len(nums)} règles, {accord} accords, {desaccord} écarts avec le script réseau")


if __name__ == "__main__":
    main()
