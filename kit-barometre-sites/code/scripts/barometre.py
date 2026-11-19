#!/usr/bin/env python3
"""Enchaîne le baromètre qualité des sites (Opquast V5), du référentiel jusqu'au rapport et au CSV.

Les étapes automatiques sont lancées dans l'ordre, chacune avec ses propres règles de prudence (une requête toutes
les 6 à 10 s par site, respect des 429, aucune commande, aucun envoi de formulaire, aucun contournement
d'anti-robot). Trois étapes ne sont PAS dans ce script parce qu'elles demandent Claude ou une personne : les
lectures IA indépendantes (sous-agents, voir la skill barometre-sites), l'export des résultats du robot
d'eServices Manager, et la publication (page Artifact, saisie dans eServices Manager, commit).

Étapes (dans l'ordre) :
  referentiel  répartition des 245 règles en volets (referentiel/repartition-regles.csv)
  moteur       moteur libre Opquast devtools, cloné et construit hors du dépôt s'il manque
  mesure       scripts réseau et page, W3C i18n, REDbot, axe-core, IBM, Lighthouse, Pa11y, sitemap, aria
  releve       relevé navigateur, parcours sans commande, décisions du relevé
  sources      deuxièmes sources : axe et IBM complémentaires, Shopify public, HTML brut et CSS, curl, panier,
               outils tiers (moteur Opquast, Alfa, Sa11y, html-validate)
  synthese     vérification des citations, fusion, état, lecture critique, suivi HTML, export CSV

Usage :
  python3 scripts/barometre.py --hors <dossier hors dépôt>                    # tout
  python3 scripts/barometre.py --hors <dossier> --etapes synthese             # seulement le rapport et le CSV
  python3 scripts/barometre.py --hors <dossier> --depuis sources --service "Boutique A"
  python3 scripts/barometre.py --hors <dossier> --essai                       # affiche les commandes sans rien lancer
  python3 scripts/barometre.py --hors <dossier> --nuit                        # passage de nuit (voir ci-dessous)

Passage de nuit (--nuit) : un passage complet dure plusieurs heures. L'option vérifie que l'ordinateur est branché sur
secteur (macOS : pmset), empêche la mise en veille pendant tout le passage (macOS : caffeinate -dimsu ; Linux :
systemd-inhibit ; Windows : non géré, régler l'alimentation à la main) et écrit tout dans un journal daté
(resultats/journal-barometre-AAAA-MM-JJ.log) à lire le matin. Sans secteur, il s'arrête (sauf --forcer).

<dossier hors dépôt> reçoit ce qui ne doit pas entrer dans Git : textes des pages légales, DOM, captures, moteur
Opquast. Les résultats versionnés vont dans resultats/<outil>-AAAA-MM-JJ/.
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
ORDRE = ["referentiel", "moteur", "mesure", "releve", "sources", "synthese"]


def etapes(hors: Path, service: list[str]) -> dict[str, list[list[str]]]:
    py, nd = [sys.executable], ["node"]
    textes, moteur = str(hors / "textes"), hors / "opquast-devtools"
    return {
        "referentiel": [py + ["scripts/repartir_regles.py"]],
        "moteur": [] if (moteur / "public" / "engine" / "rules.json").exists() else [
            ["git", "clone", "-q", "--depth", "1", "--recurse-submodules", "https://github.com/opquast-oss/opquast-devtools.git", str(moteur)],
            ["node", str(moteur / "scripts" / "sync-assets.mjs")]],
        "mesure": [
            py + ["scripts/controles_reseau.py"] + service,
            nd + ["scripts/page_playwright.mjs"] + service,
            py + ["scripts/i18n_w3c.py"] + service,
            py + ["scripts/redbot_local.py"] + service,
            nd + ["scripts/axe_playwright.mjs"] + service,
            py + ["scripts/synthese_axe.py", "@dernier:axe"],
            nd + ["scripts/outils_page.mjs"] + service,
            nd + ["scripts/outils_j2.mjs", "--sans", "psi,blacklight"] + service,
            py + ["scripts/controles_aria.py"]],
        "releve": [
            nd + ["scripts/releve_regles.mjs", textes] + service,
            nd + ["scripts/parcours.mjs"] + service,
            py + ["scripts/regles_releve.py", textes]],
        "sources": [
            nd + ["scripts/sources_page.mjs"] + service,
            py + ["scripts/sources_shopify.py", textes],
            py + ["scripts/sources_html.py"],
            py + ["scripts/sources_html2.py"],
            py + ["scripts/sources_curl.py"],
            nd + ["scripts/sources_panier.mjs", str(hors)],
            nd + ["scripts/sources_tiers.mjs", str(moteur / "public" / "engine"), str(hors)] + service],
        "synthese": [
            py + ["scripts/verifier_citations.py", textes],
            py + ["scripts/fusion_scripts.py"],
            py + ["scripts/etat_barometre.py"],
            py + ["scripts/lecture_critique.py"],
            py + ["scripts/generer_suivi.py"],
            py + ["scripts/exporter_csv.py"]],
    }


def resoudre(cmd: list[str]) -> list[str]:
    """« @dernier:axe » devient le dernier dossier resultats/axe-AAAA-MM-JJ."""
    out = []
    for x in cmd:
        if x.startswith("@dernier:"):
            l = sorted((RACINE / "resultats").glob(x.split(":", 1)[1] + "-*"))
            x = str(l[-1]) if l else x
        out.append(x)
    return out


def nuit(a) -> int:
    """Relance le passage avec la mise en veille bloquée, sur secteur, sortie copiée dans un journal daté."""
    systeme = platform.system()
    if systeme == "Darwin":
        batt = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
        if "AC Power" not in batt:
            print("L'ordinateur est sur batterie : branchez-le sur secteur avant un passage de nuit (ou --forcer).", file=sys.stderr)
            if not a.forcer:
                return 4
        bloque = ["caffeinate", "-dimsu"]
    elif systeme == "Linux" and shutil.which("systemd-inhibit"):
        bloque = ["systemd-inhibit", "--what=sleep:idle", "--why=Barometre qualite des sites"]
    else:
        print("Mise en veille non bloquée automatiquement sur ce système : réglez l'alimentation sur « jamais » "
              "(Windows : Paramètres > Système > Alimentation, ou PowerToys Awake).", file=sys.stderr)
        bloque = []
    journal = RACINE / "resultats" / f"journal-barometre-{time.strftime('%Y-%m-%d')}.log"
    args = [x for x in sys.argv[1:] if x not in ("--nuit", "--forcer")]
    cmd = bloque + [sys.executable, str(Path(__file__).resolve())] + args
    print(f"Passage de nuit lancé ({' '.join(bloque) or 'sans blocage de veille'}). Journal : {journal}", flush=True)
    with journal.open("a", encoding="utf-8") as j:
        j.write(f"\n===== début {time.strftime('%Y-%m-%d %H:%M:%S')} : {' '.join(cmd)}\n")
        j.flush()
        r = subprocess.run(cmd, cwd=RACINE, stdout=j, stderr=subprocess.STDOUT, env={**os.environ, "BAROMETRE_EVEILLE": "1"})
        j.write(f"===== fin {time.strftime('%Y-%m-%d %H:%M:%S')}, code {r.returncode}\n")
    print(f"Terminé (code {r.returncode}). Voir {journal}")
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hors", required=True, help="dossier hors dépôt (textes, DOM, captures, moteur Opquast)")
    ap.add_argument("--etapes", help="étapes à lancer, séparées par des virgules (défaut : toutes)")
    ap.add_argument("--depuis", choices=ORDRE, help="lancer à partir de cette étape")
    ap.add_argument("--service", help="un seul site (nom exact de scripts/ecrans_en_ligne.csv)")
    ap.add_argument("--essai", action="store_true", help="afficher les commandes sans les lancer")
    ap.add_argument("--continuer", action="store_true", help="ne pas s'arrêter quand une commande échoue")
    ap.add_argument("--nuit", action="store_true", help="passage de nuit : secteur vérifié, veille bloquée, journal daté")
    ap.add_argument("--forcer", action="store_true", help="avec --nuit : lancer même sur batterie")
    a = ap.parse_args()
    if a.nuit and not os.environ.get("BAROMETRE_EVEILLE"):
        return nuit(a)
    hors = Path(a.hors).resolve()
    hors.mkdir(parents=True, exist_ok=True)
    (hors / "textes").mkdir(exist_ok=True)
    choix = a.etapes.split(",") if a.etapes else ORDRE[ORDRE.index(a.depuis):] if a.depuis else ORDRE
    inconnues = [e for e in choix if e not in ORDRE]
    if inconnues:
        print(f"Étape inconnue : {', '.join(inconnues)} (attendu : {', '.join(ORDRE)})", file=sys.stderr)
        return 2
    plan = etapes(hors, ["--service", a.service] if a.service else [])
    # prérequis : rien n'est lancé s'il manque un outil (le moteur Opquast est construit par l'étape « moteur »)
    if not a.essai and any(e in choix for e in ("mesure", "releve", "sources")):
        if subprocess.run([sys.executable, "scripts/verifier_installation.py"], cwd=RACINE).returncode != 0:
            print("\nPrérequis manquants : montrer cette liste à la personne et n'installer qu'avec son accord "
                  "(python3 scripts/verifier_installation.py --installer), puis relancer.", file=sys.stderr)
            return 3
    bilan = []
    for e in [x for x in ORDRE if x in choix]:
        print(f"\n=== {e}", flush=True)
        for cmd in plan[e]:
            cmd = resoudre(cmd)
            print("  $", " ".join(f'"{c}"' if " " in c else c for c in cmd), flush=True)
            if a.essai:
                continue
            t = time.time()
            r = subprocess.run(cmd, cwd=RACINE)
            bilan.append((e, Path(cmd[1]).name if len(cmd) > 1 else cmd[0], r.returncode, round(time.time() - t)))
            if r.returncode != 0 and not a.continuer:
                print(f"\nÉchec ({r.returncode}) : {' '.join(cmd)}. Corriger puis relancer avec --depuis {e}.", file=sys.stderr)
                return r.returncode
    if bilan:
        print("\nBilan :")
        for e, nom, code, s in bilan:
            print(f"  {'ok ' if code == 0 else 'ÉCHEC'} {e:<11} {nom:<26} {s} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
