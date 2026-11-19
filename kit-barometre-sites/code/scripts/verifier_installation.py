#!/usr/bin/env python3
"""Vérifie, sur l'ordinateur où tourne le baromètre, tout ce dont la chaîne a besoin, et dit comment installer ce qui
manque. Ne modifie RIEN sans --installer, et --installer ne doit être lancé qu'après l'accord explicite de la personne
(la skill barometre-sites lui montre d'abord la liste produite ici).

Vérifie : Node.js 22 ou plus et npm ; les paquets npm du projet (package.json, versions épinglées) ; le navigateur
Chromium de Playwright ; Python 3.10 ou plus et l'environnement .venv avec ses paquets (requirements.txt) ; les outils
système git, curl, dig, xmllint, pdftotext, pdftoppm et pdfinfo ; le moteur libre Opquast devtools (construit par
l'étape « moteur », signalé ici seulement).

Usage :
  python3 scripts/verifier_installation.py                 # liste, sans rien installer
  python3 scripts/verifier_installation.py --hors <dossier>  # vérifie aussi le moteur Opquast dans ce dossier
  python3 scripts/verifier_installation.py --installer     # installe ce qui manque (après accord)
Code de sortie : 0 si tout est prêt, 1 s'il manque quelque chose.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
MAC = platform.system() == "Darwin"


def sortie(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=RACINE).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def version(txt: str) -> tuple[int, ...]:
    m = re.search(r"(\d+)\.(\d+)", txt)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def outil_systeme(nom: str, paquet_mac: str, paquet_linux: str) -> tuple[str, bool, str, str]:
    ok = shutil.which(nom) is not None
    cmd = (f"brew install {paquet_mac}" if MAC else f"sudo apt-get install -y {paquet_linux}")
    return (nom, ok, "présent" if ok else "absent", cmd)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hors", help="dossier hors dépôt où le moteur Opquast est construit")
    ap.add_argument("--installer", action="store_true", help="installer ce qui manque (seulement après accord)")
    a = ap.parse_args()
    lignes: list[tuple[str, bool, str, str]] = []

    nv = sortie(["node", "-v"])
    lignes.append(("Node.js 22 ou plus", version(nv) >= (22, 0), nv or "absent",
                   "brew install node" if MAC else "installer Node.js 22 (https://nodejs.org)"))
    lignes.append(("npm", bool(sortie(["npm", "-v"])), sortie(["npm", "-v"]) or "absent", "fourni avec Node.js"))

    pkg = json.loads((RACINE / "package.json").read_text(encoding="utf-8"))
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    manquants = [n for n in deps if not (RACINE / "node_modules" / n / "package.json").exists()]
    lignes.append((f"paquets npm du projet ({len(deps)})", not manquants,
                   "tous présents" if not manquants else "manquants : " + ", ".join(manquants),
                   "npm ci --ignore-scripts"))

    chem = sortie(["node", "-e", "try{console.log(require('playwright').chromium.executablePath())}catch(e){}"])
    lignes.append(("navigateur Chromium de Playwright", bool(chem) and Path(chem).exists(), "présent" if chem and Path(chem).exists() else "absent",
                   "npx playwright install chromium"))

    pv = sortie([sys.executable, "--version"])
    lignes.append(("Python 3.10 ou plus", version(pv) >= (3, 10), pv, "brew install python" if MAC else "sudo apt-get install -y python3 python3-venv"))
    venv = RACINE / ".venv" / "bin" / "python"
    req = [l.split("==")[0].strip() for l in (RACINE / "requirements.txt").read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    installes = sortie([str(venv), "-m", "pip", "list", "--format=freeze"]).lower() if venv.exists() else ""
    manq_py = [p for p in req if f"{p.lower()}==" not in installes]
    lignes.append(("environnement Python .venv et ses paquets", venv.exists() and not manq_py,
                   "absent" if not venv.exists() else ("tous présents" if not manq_py else "manquants : " + ", ".join(manq_py)),
                   "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"))

    lignes += [outil_systeme("git", "git", "git"), outil_systeme("curl", "curl", "curl"),
               outil_systeme("dig", "bind", "dnsutils"), outil_systeme("xmllint", "libxml2", "libxml2-utils")]
    for nom in ("pdftotext", "pdftoppm", "pdfinfo"):
        lignes.append(outil_systeme(nom, "poppler", "poppler-utils"))

    if a.hors:
        moteur = Path(a.hors) / "opquast-devtools" / "public" / "engine" / "rules.json"
        lignes.append(("moteur libre Opquast devtools", moteur.exists(), "construit" if moteur.exists() else "absent",
                       "étape « moteur » de scripts/barometre.py (clone opquast-oss/opquast-devtools et construit le moteur)"))

    larg = max(len(l[0]) for l in lignes)
    print("Prérequis du baromètre des sites\n")
    for nom, ok, etat, cmd in lignes:
        print(f"  {'ok      ' if ok else 'MANQUE  '} {nom:<{larg}}  {etat}" + ("" if ok else f"\n           installer : {cmd}"))
    manque = [l for l in lignes if not l[1]]
    print(f"\n{'Tout est prêt.' if not manque else f'{len(manque)} élément(s) à installer.'}")
    print("Hors de cet ordinateur : le connecteur MCP Opquast (protocole des règles) et l'accès à eServices Manager, à vérifier dans Claude.")

    if a.installer and manque:
        print("\nInstallation (accord donné) :")
        deja = set()
        for nom, ok, etat, cmd in manque:
            if cmd in deja or cmd.startswith(("installer", "fourni", "étape")):
                continue
            deja.add(cmd)
            print(f"  $ {cmd}", flush=True)
            r = subprocess.run(cmd, shell=True, cwd=RACINE)  # nosec B602: commandes d'installation écrites dans ce script, lancées après accord
            if r.returncode != 0:
                print(f"    échec ({r.returncode}) : à faire à la main", file=sys.stderr)
        return main_sans_installer()
    return 1 if manque else 0


def main_sans_installer() -> int:
    sys.argv = [a for a in sys.argv if a != "--installer"]
    return main()


if __name__ == "__main__":
    sys.exit(main())
