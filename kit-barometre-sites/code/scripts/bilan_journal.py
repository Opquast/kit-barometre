#!/usr/bin/env python3
"""Bloc final du dernier passage du baromètre : étapes réussies, échecs avec leur commande, commande de reprise.

À lancer le matin, à la place de relire le journal de nuit (plusieurs milliers de lignes). Lit l'état machine du
passage (resultats/etat-passage-AAAA-MM-JJ.json, écrit par barometre.py) ; à défaut, ou s'il est plus ancien que le
dernier journal, lit le dernier journal (resultats/journal-barometre-AAAA-MM-JJ.log), segment du dernier lancement.

Codes de sortie : 0 tout a réussi ; 1 au moins un échec (la commande de reprise est affichée) ; 2 rien à lire ;
3 passage non terminé (encore en cours, ou interrompu : la reprise proposée part de la dernière étape commencée).

Usage :
  python3 scripts/bilan_journal.py                       # le plus récent des deux
  python3 scripts/bilan_journal.py --journal <fichier.log>
  python3 scripts/bilan_journal.py --etat <etat-passage.json>
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
ORDRE = ["referentiel", "moteur", "mesure", "releve", "sources", "synthese"]
DATE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def dernier(motif: str) -> Path | None:
    l = sorted((RACINE / "resultats").glob(motif))
    return l[-1] if l else None


def date_de(f: Path | None) -> str:
    m = DATE.search(f.name) if f else None
    return m.group(1) if m else ""


def depuis_etat(etat: dict) -> dict:
    etapes = [(e, v["statut"], [c["nom"] for c in v["commandes"]]) for e, v in etat.get("etapes", {}).items()]
    reprise = etat.get("reprise")
    if not etat.get("termine"):
        en_cours = next((e for e, st, _ in etapes if st in ("en cours", "échec")), None) or next((e for e, st, _ in etapes if st == "à faire"), None)
        reprise = reprise or (en_cours and shlex.join(["python3", "scripts/barometre.py", "--hors", etat.get("hors", "<hors>"), "--depuis", en_cours]))
    return {"etapes": etapes, "echecs": [(x["etape"], x["commande"], x["code"]) for x in etat.get("echecs", [])],
            "reprise": reprise, "termine": bool(etat.get("termine"))}


def reprise_journal(lancement: str, etape: str) -> str:
    """Reconstruit la commande de reprise depuis la ligne « ===== début » du journal (anciens journaux)."""
    mots = shlex.split(lancement)
    args = mots[next((i for i, m in enumerate(mots) if m.endswith("barometre.py")), len(mots) - 1) + 1:]
    garde, saute = [], False
    for m in args:
        if saute:
            saute = False
        elif m in ("--depuis", "--etapes"):
            saute = True
        elif m not in ("--continuer", "--arreter"):
            garde.append(m)
    return shlex.join(["python3", "scripts/barometre.py"] + garde + ["--depuis", etape])


def depuis_journal(texte: str) -> dict | None:
    segment = texte.split("\n===== début")[-1]
    m = re.search(r"^État du passage : (.+)$", segment, re.M)
    if m and Path(m.group(1).strip()).is_file():
        return depuis_etat(json.loads(Path(m.group(1).strip()).read_text(encoding="utf-8")))
    lancement = segment.split("\n", 1)[0].split(" : ", 1)[-1]
    vues = re.findall(r"^=== (\w+)$", segment, re.M)
    if not vues:
        return None
    lignes = re.findall(r"^  (ok|ÉCHEC)\s+(\w+)\s+(\S+)", segment, re.M)
    echecs = [(e, nom) for st, e, nom in lignes if st == "ÉCHEC"]
    arret = re.search(r"^Échec \((\d+)\) : (.+?)\. Corriger puis relancer avec --depuis (\w+)\.$", segment, re.M)
    sortie = []
    for e, nom in echecs:
        cmd = next((c for c in re.findall(r"^  \$ (.+)$", segment.split(f"=== {e}\n", 1)[-1], re.M) if nom in c), nom)
        sortie.append((e, cmd, None))
    if arret:
        sortie.append((arret.group(3), arret.group(2), int(arret.group(1))))
    termine = "\n===== fin" in segment
    faites = {e for st, e, _ in lignes if st == "ok"} - {e for e, *_ in sortie}
    etapes = [(e, "échec" if e in {x[0] for x in sortie} else "fait" if e in faites or termine else "commencée", []) for e in vues]
    premier = sortie[0][0] if sortie else (vues[-1] if not termine else None)
    return {"etapes": etapes, "echecs": sortie, "termine": termine,
            "reprise": reprise_journal(lancement, premier) if premier else None}


def afficher(b: dict, source: Path) -> int:
    print(f"Bilan du passage ({source.name})")
    for e, st, noms in b["etapes"]:
        print(f"  {st:<9} {e}" + (f" ({len(noms)} commande(s))" if noms else ""))
    print(f"Échecs : {len(b['echecs'])}")
    for e, cmd, code in b["echecs"]:
        print(f"  {e} : {cmd}" + (f" (code {code})" if code is not None else ""))
    if not b["termine"]:
        print("Passage non terminé : encore en cours, ou interrompu (vérifier qu'aucun barometre.py ne tourne).")
    if b["reprise"]:
        print(f"Reprise : {b['reprise']}")
    return 3 if not b["termine"] else 1 if b["echecs"] else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--journal", type=Path, help="journal de nuit à lire")
    ap.add_argument("--etat", type=Path, help="état du passage à lire")
    a = ap.parse_args(argv)
    etat, journal = a.etat, a.journal
    if not etat and not journal:
        etat, journal = dernier("etat-passage-*.json"), dernier("journal-barometre-*.log")
        if etat and journal:
            # l'état du même jour est plus riche que le journal ; un journal plus récent l'emporte
            etat, journal = (etat, None) if date_de(etat) >= date_de(journal) else (None, journal)
    if etat and etat.is_file():
        return afficher(depuis_etat(json.loads(etat.read_text(encoding="utf-8"))), etat)
    if journal and journal.is_file():
        b = depuis_journal(journal.read_text(encoding="utf-8", errors="replace"))
        if b:
            return afficher(b, journal)
    print("Rien à lire : aucun état de passage (resultats/etat-passage-*.json) ni journal lisible "
          "(resultats/journal-barometre-*.log).", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
