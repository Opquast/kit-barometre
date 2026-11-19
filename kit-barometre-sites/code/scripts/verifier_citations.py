#!/usr/bin/env python3
"""Vérifie que chaque citation d'une lecture IA indépendante existe mot pour mot dans les textes lus.

Une lecture IA est une source probabiliste : un « conforme » n'est retenu comme source que si le passage cité
(entre « ») se retrouve dans les textes du site (espaces et apostrophes normalisés). Ajoute un 4e élément
« citation vérifiée » / « citation introuvable » à chaque résultat C.

Usage : python3 scripts/verifier_citations.py <dossier des textes, hors dépôt>
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKC", t).replace("’", "'").replace(" ", " ").lower()
    return re.sub(r"[^\w']+", " ", t).strip()


def main() -> None:
    textes = Path(sys.argv[1])
    for f in sorted(RACINE.glob("resultats/sources-*/lecture_ia_lot*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        # sans les textes (dossier temporaire vidé), on garde la vérification déjà faite au lieu de tout rejeter
        if not any(textes.glob("*.txt")):
            print(f.name, "textes absents : vérification précédente conservée")
            continue
        bilan = {}
        for site, regles in d.items():
            prefixe = re.sub(r"[^A-Za-z0-9_]+", "_", site)
            corpus = norm(" ".join(p.read_text(encoding="utf-8") for p in textes.glob(f"{prefixe}__*.txt")))
            ok = ko = 0
            for k, v in regles.items():
                v[:] = v[:3]
                if v[0] != "C":
                    continue
                cit = [c for c in re.findall(r"«\s*([^»]+?)\s*»", v[1]) if len(c) > 4]
                trouve = bool(cit) and all(any(norm(m) in corpus for m in re.split(r"\s*(?:\[masqué\]|\.\.\.|…)\s*", c) if len(norm(m)) > 3) for c in cit)
                v.append("citation vérifiée" if trouve else "citation introuvable")
                ok += trouve; ko += not trouve
            bilan[site] = (ok, ko)
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f.name, bilan)
    # 13/11 : lectures du DOM et des captures : un extrait « dom: fichier | extrait » doit exister mot pour mot dans le
    # fichier cité ; une preuve « capture: … » (jugement visuel) est gardée comme telle.
    hors = textes.parent
    for f in sorted(RACINE.glob("resultats/sources-*/lecture_dom_lot*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        bilan = {}
        for site, regles in d.items():
            ok = ko = vis = 0
            for k, v in regles.items():
                avant = v[3] if len(v) > 3 else None
                v[:] = v[:3]
                if v[0] not in ("C", "NC", "NA"):
                    continue
                m_ = re.match(r"\s*dom:\s*([^|]+?)\s*\|", v[1])
                if m_ and avant and not any(hors.rglob(m_.group(1).strip().split("/")[-1])):
                    v.append(avant)  # fichier absent (dossier temporaire vidé) : vérification précédente conservée
                    ok += avant == "extrait vérifié"
                    continue
                m = re.match(r"\s*dom:\s*([^|]+?)\s*\|\s*(.+)$", v[1], re.S)
                if m:
                    nomf = m.group(1).strip().split("/")[-1]
                    cible = next((p for p in hors.rglob(nomf)), None)
                    contenu = norm(cible.read_text(encoding="utf-8", errors="replace")) if cible else ""
                    morceaux = [x for x in re.split(r"\s*(?:\[masqué\]|\.\.\.|…)\s*", m.group(2).strip().strip("«»\"' ")) if len(norm(x)) > 3]
                    trouve = bool(contenu) and bool(morceaux) and all(norm(x) in contenu for x in morceaux)
                    v.append("extrait vérifié" if trouve else "extrait introuvable"); ok += trouve; ko += not trouve
                elif v[1].strip().startswith("capture:"):
                    v.append("jugement visuel"); vis += 1
                else:
                    v.append("preuve absente"); ko += 1
            bilan[site] = (ok, ko, vis)
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f.name, "vérifiés, rejetés, visuels :", bilan)


if __name__ == "__main__":
    main()
