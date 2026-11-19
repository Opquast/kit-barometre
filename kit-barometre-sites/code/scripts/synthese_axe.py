#!/usr/bin/env python3
"""Synthèse des résultats axe-core (WCAG 2.1 A et AA) par site.

Entrée : resultats/axe-AAAA-MM-JJ/brut.tsv (une ligne par page, rempli avec scripts/axe_navigateur.js).
Sorties : rapport.md et resultats.json dans le même dossier.

Usage : python3 scripts/synthese_axe.py resultats/axe-2026-11-12
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

# Libellé en français de chaque règle axe-core rencontrée, et critère WCAG correspondant.
LIBELLES = {
    "button-name": "Bouton sans nom accessible",
    "nested-interactive": "Éléments interactifs imbriqués",
    "link-name": "Lien sans intitulé accessible",
    "color-contrast": "Contraste du texte insuffisant",
    "list": "Liste mal structurée",
    "listitem": "Élément de liste hors d'une liste",
    "scrollable-region-focusable": "Zone défilante inaccessible au clavier",
    "aria-prohibited-attr": "Attribut ARIA interdit sur cet élément",
    "aria-hidden-focus": "Élément masqué aux lecteurs d'écran mais atteignable au clavier",
    "image-alt": "Image sans texte alternatif",
    "meta-viewport": "Zoom bloqué sur mobile",
    "label": "Champ de formulaire sans étiquette",
    "select-name": "Liste déroulante sans nom accessible",
    "aria-valid-attr-value": "Valeur d'attribut ARIA invalide",
}
GRAVITE = {"critical": "critique", "serious": "sérieuse", "moderate": "modérée", "minor": "mineure"}


def critere(tag: str) -> str:
    """wcag143 -> 1.4.3"""
    chiffres = tag.replace("wcag", "")
    return ".".join([chiffres[0], chiffres[1], chiffres[2:]])


def main() -> None:
    dossier = Path(sys.argv[1] if len(sys.argv) > 1 else "resultats/axe-2026-11-12")
    lignes = list(csv.DictReader((dossier / "brut.tsv").open(encoding="utf-8"), delimiter="\t"))
    sites: dict[str, dict] = {}
    for l in lignes:
        s = sites.setdefault(l["service"], {"pages": [], "regles": {}})
        teste = l["regles_respectees"] != "NT"
        page = {"gabarit": l["gabarit"], "chemin": l["chemin"], "teste": teste, "violations": []}
        if teste:
            page["regles_respectees"] = int(l["regles_respectees"])
            page["a_verifier"] = int(l["a_verifier"])
            for v in filter(None, l["violations"].split(";")):
                rid, impact, tags, n = v.split(":")
                crits = [critere(t) for t in tags.split()]
                page["violations"].append({"regle": rid, "gravite": impact, "criteres": crits, "elements": int(n)})
                r = s["regles"].setdefault(rid, {"gravite": impact, "criteres": crits, "pages": 0, "elements": 0})
                r["pages"] += 1
                r["elements"] += int(n)
        s["pages"].append(page)

    out = {"outil": "axe-core 4.10.2", "referentiel": "WCAG 2.1 A et AA", "date": dossier.name.replace("axe-", ""), "sites": {}}
    md = [f"# Accessibilité automatique (axe-core 4.10.2, WCAG 2.1 A et AA) du {out['date']}", "",
          "Contrôle dans le navigateur, page par page (`scripts/axe_navigateur.js`). Même version et mêmes règles à chaque mesure.",
          "axe-core détecte automatiquement une partie seulement des problèmes d'accessibilité : le reste relève de l'audit IA et humain.", "",
          "## Synthèse", "", "| Site | Pages testées | Règles en violation | Dont critiques | Éléments en défaut |", "|---|---|---|---|---|"]
    for nom, s in sites.items():
        testees = [p for p in s["pages"] if p["teste"]]
        crit = [r for r, v in s["regles"].items() if v["gravite"] == "critical"]
        tot = sum(v["elements"] for v in s["regles"].values())
        out["sites"][nom] = {"pages_testees": len(testees), "pages_non_testees": len(s["pages"]) - len(testees),
                             "regles_en_violation": len(s["regles"]), "regles_critiques": len(crit), "elements_en_defaut": tot,
                             "regles": s["regles"], "pages": s["pages"]}
        md.append(f"| {nom} | {len(testees)} sur {len(s['pages'])} | {len(s['regles'])} | {len(crit)} | {tot} |")
    md.append("")
    for nom, s in sites.items():
        md += [f"## {nom}", "", "| Problème | Règle axe-core | Critère WCAG | Gravité | Pages | Éléments |", "|---|---|---|---|---|---|"]
        for rid, v in sorted(s["regles"].items(), key=lambda kv: (kv[1]["gravite"] != "critical", -kv[1]["pages"])):
            md.append(f"| {LIBELLES.get(rid, rid)} | `{rid}` | {', '.join(v['criteres'])} | {GRAVITE.get(v['gravite'], v['gravite'])} | {v['pages']} | {v['elements']} |")
        nt = [p for p in s["pages"] if not p["teste"]]
        if nt:
            md.append("")
            md += [f"- Non testé : {p['gabarit']} ({p['chemin']})." for p in nt]
        md.append("")
    md += ["## Observations faites pendant le passage", "",
           "- Les comptes clients de Boutique A, Boutique C, Boutique D et Boutique E sont hébergés par Shopify (comptes clients Shopify) : hors périmètre, axe-core y est bloqué.",
           "- Chez Boutique B et Boutique F, l'adresse /cart ouvre le panier en tiroir sur l'accueil.",
           "- Chez Boutique D, le panier de la version française (/fr/cart) renvoie vers l'accueil en anglais : perte de la langue choisie, à relier aux règles Opquast d'internationalisation.",
           "- Les pages que Shopify refuse au script réseau (code 429) passent sans problème dans le navigateur."]
    (dossier / "rapport.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (dossier / "resultats.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{dossier}/rapport.md : {len(sites)} sites")


if __name__ == "__main__":
    main()
