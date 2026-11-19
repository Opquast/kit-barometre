#!/usr/bin/env python3
"""Valide les sorties des lectures IA indépendantes avant la synthèse.

Pour chaque lecture décrite dans referentiel/lectures.json, lit les fichiers du dernier passage qui en contient
(resultats/sources-<date>/lecture_ia_lot*.json, lecture_visuelle_lot*.json, lecture_dom_lot*.json) et vérifie chaque
entrée {"Site": {"12": [statut, preuve, nature, (vérification)]}} :
- statut dans C, NC, NA, NT ;
- site connu du parc (referentiel/parc.json) ;
- règle dans la liste de sa lecture (lecture 3 : <hors>/regles_une_source.json si <hors> est donné, sinon 1 à 245) ;
- preuve au format de la lecture (citation, capture ou dom), fichier cité appartenant au site ;
- fichier cité présent dans <hors> (textes, captures, dom, paiement) si <hors> est donné et que ces dossiers ne sont
  pas vides (dossier temporaire vidé entre deux sessions : existence non vérifiée, on le dit).

Les fonctions erreurs_entree et charger_lectures servent aussi à scripts/lecture_critique.py, qui écarte les
entrées invalides.

Usage : python3 scripts/valider_lectures.py [<hors>] [--exiger 1,2]
  --exiger : lectures dont une sortie doit exister (sinon erreur).
Codes de sortie : 0 tout est valide (ou aucune sortie, sans --exiger), 1 erreurs (liste affichée), 2 usage.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import parc

RACINE = Path(__file__).resolve().parent.parent
STATUTS = ("C", "NC", "NA", "NT")
NB_REGLES = 245
CITATION_MOTS_MAX = 25
EXTRAIT_MIN, EXTRAIT_MAX = 20, 160
DOSSIERS_HORS = ("textes", "captures", "dom", "paiement")
EXT_CAPTURE = (".jpg", ".jpeg", ".png")
RE_CITATION = re.compile(r"«\s*([^»]+?)\s*»")
RE_TEXTE = re.compile(r"\(([^()]+?\.txt)\)")
RE_CAPTURE = re.compile(r"\s*capture:\s*([^|]+?)\s*\|\s*(\S.*)$", re.S)
RE_DOM = re.compile(r"\s*dom:\s*([^|]+?)\s*\|\s*(.+)$", re.S)


def charger_lectures(racine: Path | None = None) -> dict:
    return json.loads(((racine or RACINE) / "referentiel" / "lectures.json").read_text(encoding="utf-8"))


def prefixe(site: str) -> str:
    """Préfixe des fichiers d'un site (même règle que sources_tiers.mjs et verifier_citations.py)."""
    return re.sub(r"[^A-Za-z0-9_]+", "_", site)


def sites_parc(racine: Path | None = None) -> set[str]:
    return set(parc.par_nom((racine or RACINE) / "referentiel" / "parc.json"))


def regles_une_source(hors: Path | None) -> dict | None:
    f = hors / "regles_une_source.json" if hors else None
    return json.loads(f.read_text(encoding="utf-8")) if f and f.is_file() else None


def index_hors(hors: Path | None) -> set[str] | None:
    """Noms des fichiers présents dans les dossiers d'entrée de <hors> ; None si rien à vérifier."""
    if hors is None:
        return None
    noms = {p.name for d in DOSSIERS_HORS if (hors / d).is_dir() for p in (hors / d).rglob("*") if p.is_file()}
    return noms or None


def base(chemin: str) -> str:
    return chemin.strip().replace("\\", "/").split("/")[-1]


def _fichier(nom: str, pref: str, index: set[str] | None, paiement_permis: bool) -> list[str]:
    b = base(nom)
    du_site = b.startswith(pref + "__") or (paiement_permis and b.rsplit(".", 1)[0] == pref)
    if not du_site:
        return [f"fichier « {b} » qui n'est pas un fichier du site (préfixe {pref})"]
    if index is not None and b not in index:
        return [f"fichier « {b} » introuvable dans le dossier hors dépôt"]
    return []


def erreurs_preuve(forme: str, statut: str, preuve: str, pref: str, index: set[str] | None = None, tunnel: bool = False) -> list[str]:
    """Erreurs de forme d'une preuve ; une preuve NT est libre."""
    if statut == "NT":
        return []
    if forme == "citation":
        err = []
        fichiers = RE_TEXTE.findall(preuve)
        if not fichiers:
            err.append("fichier .txt cité entre parenthèses manquant")
        for f in fichiers:
            err += _fichier(f, pref, index, False)
        cits = RE_CITATION.findall(preuve)
        if not cits and (statut == "C" or not preuve.strip().startswith("absent:")):
            err.append("citation « … » manquante" + ("" if statut == "C" else " (ou « absent: » pour un NC ou un NA)"))
        err += [f"citation de plus de {CITATION_MOTS_MAX} mots" for c in cits if len(c.split()) > CITATION_MOTS_MAX]
        return err
    m = RE_CAPTURE.match(preuve)
    if m:
        f = m.group(1)
        if not base(f).lower().endswith(EXT_CAPTURE):
            return [f"capture « {base(f)} » qui n'est pas une image (.jpg)"]
        err = _fichier(f, pref, index, forme == "dom_ou_capture")
    elif forme == "dom_ou_capture" and (m := RE_DOM.match(preuve)):
        f = m.group(1)
        extrait = m.group(2).strip().strip("«»\"' ")
        err = _fichier(f, pref, index, True)
        if not EXTRAIT_MIN <= len(extrait) <= EXTRAIT_MAX:
            err.append(f"extrait DOM de {len(extrait)} caractères (attendu {EXTRAIT_MIN} à {EXTRAIT_MAX})")
    else:
        attendu = "« capture: fichier.jpg | ce qui est vu »" + (" ou « dom: fichier | extrait »" if forme == "dom_ou_capture" else "")
        return [f"preuve hors format (attendu {attendu})"]
    if tunnel and not (base(f).rsplit(".", 1)[0] == pref or "paiement/" in f.replace("\\", "/")):
        err.append("règle du tunnel jugée hors de paiement/ (attendu NT)")
    return err


def regles_permises(cfg: dict, site: str, regles3: dict | None) -> set[str] | None:
    """Règles admises pour ce site ; None : toute règle de 1 à 245."""
    if cfg["regles"] == "regles_une_source":
        return None if regles3 is None else {str(k) for k in regles3.get(site, [])}
    return {str(k) for k in cfg["regles"]}


def erreurs_entree(cfg: dict, site: str, regle: str, v, sites: set[str], index: set[str] | None = None, regles3: dict | None = None) -> list[str]:
    """Erreurs d'une entrée de lecture (liste vide : entrée valide)."""
    if site not in sites:
        return ["site inconnu du parc (referentiel/parc.json)"]
    permises = regles_permises(cfg, site, regles3)
    k = str(regle)
    if permises is None:
        if not (k.isdigit() and 1 <= int(k) <= NB_REGLES):
            return [f"règle « {k} » hors du référentiel (1 à {NB_REGLES})"]
    elif k not in permises:
        return [f"règle « {k} » hors de la liste de la lecture {cfg['nom']}"]
    if not (isinstance(v, list) and 3 <= len(v) <= 4 and all(isinstance(x, str) for x in v)):
        return ["entrée mal formée (attendu [statut, preuve, nature])"]
    if v[0] not in STATUTS:
        return [f"statut « {v[0]} » hors de C, NC, NA, NT"]
    tunnel = k in {str(x) for x in cfg.get("regles_tunnel", [])}
    return erreurs_preuve(cfg["preuve"], v[0], v[1], prefixe(site), index, tunnel)


def fichiers_dernier_passage(racine: Path, sortie: str) -> list[Path]:
    """Fichiers d'une lecture dans le dernier resultats/sources-* qui en contient."""
    motif = sortie.replace("{n}", "*")
    dossiers = [d for d in sorted(racine.glob("resultats/sources-*")) if d.is_dir() and any(d.glob(motif))]
    return sorted(dossiers[-1].glob(motif)) if dossiers else []


def lire_sortie(chemin: Path) -> tuple[dict, list[str]]:
    """Contenu d'une sortie de lecture, ou l'erreur qui empêche de la lire."""
    try:
        d = json.loads(chemin.read_text(encoding="utf-8"))
    except ValueError as e:
        return {}, [f"JSON illisible ({e})"]
    if not isinstance(d, dict):
        return {}, ["le fichier doit être un objet {site: {règle: [statut, preuve, nature]}}"]
    return d, []


def valider_fichier(chemin: Path, cfg: dict, sites: set[str], index: set[str] | None = None, regles3: dict | None = None) -> list[str]:
    d, err = lire_sortie(chemin)
    lignes = [f"{chemin.name} : {e}" for e in err]
    for site, regles in d.items():
        if not isinstance(regles, dict):
            lignes.append(f"{chemin.name} · {site} : attendu un objet {{règle: [statut, preuve, nature]}}")
            continue
        for k, v in regles.items():
            lignes += [f"{chemin.name} · {site} · règle {k} : {e}" for e in erreurs_entree(cfg, site, k, v, sites, index, regles3)]
    return lignes


def main(arguments: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Valide les sorties des lectures IA indépendantes.")
    ap.add_argument("hors", nargs="?", help="dossier hors dépôt (vérifie les fichiers cités et la liste de la lecture 3)")
    ap.add_argument("--exiger", default="", help="lectures dont une sortie doit exister, par exemple 1,2")
    try:
        a = ap.parse_args(arguments)
    except SystemExit:
        return 2
    lectures = charger_lectures()
    exiger = [x for x in a.exiger.replace(" ", "").split(",") if x]
    if any(x not in lectures["lectures"] for x in exiger):
        print(f"✖ --exiger : lectures connues {', '.join(lectures['lectures'])}", file=sys.stderr)
        return 2
    hors = Path(a.hors) if a.hors else None
    index = index_hors(hors)
    regles3 = regles_une_source(hors)
    sites = sites_parc()
    erreurs: list[str] = []
    if hors is not None and index is None:
        print(f"ℹ {hors} : textes, captures et DOM absents, existence des fichiers cités non vérifiée.")
    for num, cfg in lectures["lectures"].items():
        fichiers = fichiers_dernier_passage(RACINE, cfg["sortie"])
        if not fichiers:
            if num in exiger:
                erreurs.append(f"lecture {num} ({cfg['nom']}) : aucune sortie {cfg['sortie'].replace('{n}', '*')} dans resultats/sources-*")
            else:
                print(f"ℹ lecture {num} ({cfg['nom']}) : aucune sortie.")
            continue
        avant = len(erreurs)
        for f in fichiers:
            erreurs += valider_fichier(f, cfg, sites, index, regles3)
        print(f"{'✔' if len(erreurs) == avant else '✖'} lecture {num} ({cfg['nom']}) : {len(fichiers)} fichier(s) dans {fichiers[0].parent.name}, "
              f"{len(erreurs) - avant} erreur(s).")
    if erreurs:
        print(f"\n{len(erreurs)} erreur(s) : corriger ou relancer le sous-agent concerné, puis revalider.")
        for e in erreurs:
            print(f"  - {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
