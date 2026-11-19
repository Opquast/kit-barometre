#!/usr/bin/env python3
"""Génère les briefs des sous-agents des lectures IA indépendantes, prêts à copier.

Un brief par sous-agent dans <hors>/briefs/lecture<L>_lot<n>.md : consignes communes, sites du lot (lus dans
referentiel/parc.json) avec leur préfixe de fichiers, entrées présentes, liste dédoublonnée des règles (un seul appel
get_rule par règle, ou le protocole déjà extrait dans <hors>/protocoles/<règle>.md), forme de preuve, chemin de sortie
daté exact et format. Tout vient de referentiel/lectures.json.
Lecture 3 : une liste par site lue dans <hors>/regles_une_source.json (scripts/regles_une_source.py), un sous-agent par
site ; un site sans règle à une source n'a pas de brief.
Écrit aussi <hors>/briefs/regles_a_charger.json : l'union des règles des briefs générés, pour extraire chaque protocole
une seule fois si on le souhaite.

Usage : python3 scripts/preparer_lectures.py <hors> [--lecture 1|2|3] [--date AAAA-MM-JJ]
  sans --lecture : lectures 1 et 2 ; la lecture 3 se prépare après la synthèse et regles_une_source.py.
Codes de sortie : 0 briefs écrits, entrées complètes ; 1 entrée obligatoire manquante (briefs écrits quand même,
sauf lecture 3 sans regles_une_source.json) ou parc vide ; 2 usage.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import parc
import valider_lectures as vl

RACINE = Path(__file__).resolve().parent.parent


def lots(sites: list[str], taille: int) -> list[tuple[int, list[str]]]:
    return [(i // taille + 1, sites[i:i + taille]) for i in range(0, len(sites), taille)]


def entrees_site(hors: Path, cfg: dict, site: str) -> tuple[list[str], list[str]]:
    """(fichiers trouvés, entrées obligatoires manquantes) pour un site."""
    pref = vl.prefixe(site)
    trouves, manquants = [], []
    for e in cfg["entrees"]:
        motif = e["motif"].format(prefixe=pref)
        fichiers = sorted(p for p in (hors / e["dossier"]).glob(motif) if p.is_file()) if (hors / e["dossier"]).is_dir() else []
        trouves += [str(p) for p in fichiers]
        if not fichiers and e["obligatoire"]:
            manquants.append(f"{e['dossier']}/{motif}")
    return trouves, manquants


def brief(hors: Path, num: str, cfg: dict, n: int, sites: list[str], regles: list[int], sortie: Path, communes: list[str], bilan_max: int,
          fichiers: dict[str, list[str]], manquants: dict[str, list[str]]) -> str:
    l = [f"# Lecture {num} ({cfg['nom']}), lot {n}", "",
         "Tu es un sous-agent de lecture indépendante du baromètre qualité. Applique les consignes ci-dessous à la lettre.", "",
         "## Consignes communes", ""]
    l += [f"- {c.replace('<hors>', str(hors))}" for c in communes]
    l += [f"- Bilan rendu : {bilan_max} lignes au plus.", "", "## Sites du lot", ""]
    l += [f"- {s} : préfixe de fichiers `{vl.prefixe(s)}`" for s in sites]
    l += ["", "## Entrées (lire seulement ces fichiers)", ""]
    for e in cfg["entrees"]:
        l.append(f"- `{hors / e['dossier']}/<préfixe>{e['motif'].split('{prefixe}')[1]}` : {e['description']}" + ("" if e["obligatoire"] else " (si présent)"))
    for s in sites:
        l.append(f"\nFichiers de {s} :")
        l += [f"- `{f}`" for f in fichiers[s]] or ["- aucun fichier trouvé"]
        if manquants[s]:
            l.append(f"- ATTENTION, entrées manquantes : {', '.join(manquants[s])} (statut NT pour ce qu'elles auraient montré)")
    proto = hors / "protocoles"
    a_charger = [k for k in regles if not (proto / f"{k}.md").is_file()]
    deja = [k for k in regles if k not in a_charger]
    l += ["", f"## Règles ({len(regles)})", "", ", ".join(map(str, regles)), ""]
    if a_charger:
        l.append(f"Charger chaque protocole une seule fois, au début : get_rule pour {', '.join(map(str, a_charger))}.")
    if deja:
        l.append(f"Protocoles déjà extraits (lire `{proto}/<règle>.md`, pas de get_rule) : {', '.join(map(str, deja))}.")
    l += ["", "## Consignes propres à cette lecture", ""]
    l += [f"- {c}" for c in cfg["consignes"]]
    if cfg["regles_tunnel"]:
        l.append(f"- Règles du tunnel ({', '.join(map(str, cfg['regles_tunnel']))}) : seulement sur `{hors / 'paiement'}/`, sinon NT.")
    exemple = {sites[0]: {str(regles[0]): ["C", "<preuve au format ci-dessus>", "lecture"]}}
    l += ["", "## Preuve", "", cfg["format_preuve"], "",
          "## Sortie", "", f"Écrire exactement ce fichier (créer le dossier s'il manque) : `{sortie}`", "",
          "Format : un objet par site, une entrée par règle, `[statut, preuve, nature]` :", "",
          "```json", json.dumps(exemple, ensure_ascii=False), "```", ""]
    return "\n".join(l)


def main(arguments: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Génère les briefs des lectures IA indépendantes.")
    ap.add_argument("hors", help="dossier hors dépôt (textes, captures, dom, paiement)")
    ap.add_argument("--lecture", choices=["1", "2", "3"], help="une seule lecture (défaut : 1 et 2 ; la lecture 3 se prépare après la synthèse, avec --lecture 3)")
    ap.add_argument("--date", default=f"{date.today():%Y-%m-%d}", help="date du dossier de sortie resultats/sources-<date> (défaut : aujourd'hui)")
    try:
        a = ap.parse_args(arguments)
    except SystemExit:
        return 2
    hors = Path(a.hors).resolve()
    conf = vl.charger_lectures(RACINE)
    sites = [s["nom"] for s in parc.sites(RACINE / "referentiel" / "parc.json")]
    if not sites:
        print("✖ Parc vide (referentiel/parc.json) : aucun brief.", file=sys.stderr)
        return 1
    regles3 = vl.regles_une_source(hors)
    numeros = [a.lecture] if a.lecture else ["1", "2"]
    dossier = hors / "briefs"
    dossier.mkdir(parents=True, exist_ok=True)
    code, union, ecrits = 0, set(), []
    for num in numeros:
        cfg = conf["lectures"][num]
        for ancien in dossier.glob(f"lecture{num}_lot*.md"):
            ancien.unlink()
        if cfg["regles"] == "regles_une_source":
            if regles3 is None:
                print(f"✖ Lecture {num} : {hors / 'regles_une_source.json'} manque. Lancer d'abord la synthèse puis "
                      f"python3 scripts/regles_une_source.py {hors}.", file=sys.stderr)
                code = 1
                continue
            groupes = [(i + 1, [s]) for i, s in enumerate(sites) if regles3.get(s)]
            for s in sites:
                if not regles3.get(s):
                    print(f"ℹ Lecture {num} : {s} n'a aucune règle à une seule source, pas de sous-agent.")
        else:
            groupes = lots(sites, cfg["taille_lot"])
        for n, lot in groupes:
            regles = sorted({int(k) for s in lot for k in (regles3[s] if cfg["regles"] == "regles_une_source" else cfg["regles"])})
            fichiers, manquants = {}, {}
            for s in lot:
                fichiers[s], manquants[s] = entrees_site(hors, cfg, s)
                for m in manquants[s]:
                    print(f"⚠ Lecture {num}, {s} : entrée manquante {hors / m}")
                    code = 1
            sortie = RACINE / "resultats" / f"sources-{a.date}" / cfg["sortie"].format(n=n)
            f = dossier / f"lecture{num}_lot{n}.md"
            f.write_text(brief(hors, num, cfg, n, lot, regles, sortie, conf["consignes_communes"], conf["bilan_max_lignes"], fichiers, manquants), encoding="utf-8")
            union |= set(regles)
            ecrits.append(f"{f.name} ({', '.join(lot)} ; {len(regles)} règles) -> {sortie.name}")
    (dossier / "regles_a_charger.json").write_text(json.dumps(sorted(union)), encoding="utf-8")
    print(f"{len(ecrits)} brief(s) dans {dossier} :")
    for e in ecrits:
        print(f"  - {e}")
    print(f"{len(union)} règle(s) distinctes à charger (une fois chacune) : {dossier / 'regles_a_charger.json'}")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
