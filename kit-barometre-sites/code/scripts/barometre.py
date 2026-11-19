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
  synthese     vérification des citations et des lectures IA, fusion, état, lecture critique, suivi HTML, export
               CSV, puis la liste des règles à une seule source (<hors>/regles_une_source.json, pour la lecture 3)

Usage :
  python3 scripts/barometre.py --hors <dossier hors dépôt>                    # tout
  python3 scripts/barometre.py --hors <dossier> --etapes synthese             # seulement le rapport et le CSV
  python3 scripts/barometre.py --hors <dossier> --depuis sources --service "Boutique A"
  python3 scripts/barometre.py --hors <dossier> --essai                       # affiche les commandes sans rien lancer
  python3 scripts/barometre.py --hors <dossier> --nuit                        # passage de nuit (voir ci-dessous)

Passage de nuit (--nuit) : un passage complet dure plusieurs heures. L'option vérifie que l'ordinateur est branché sur
secteur (macOS : pmset), empêche la mise en veille pendant tout le passage (macOS : caffeinate -dimsu ; Linux :
systemd-inhibit ; Windows : non géré, régler l'alimentation à la main) et écrit tout dans un journal daté
(resultats/journal-barometre-AAAA-MM-JJ.log). Sans secteur, il s'arrête (sauf --forcer). La nuit, --continuer est
actif par défaut (un échec sur un site ne perd pas la nuit ; --arreter rétablit l'arrêt au premier échec).

État du passage : à chaque commande lancée, resultats/etat-passage-AAAA-MM-JJ.json est réécrit (étapes, commandes,
codes, durées, échecs, commande de reprise exacte). Le matin, `python3 scripts/bilan_journal.py` en affiche le bloc
final, sans relire le journal. Code de sortie : 0 si tout a réussi, sinon le code de la commande en échec (arrêt) ou
1 (avec --continuer, au moins un échec), 2 étape inconnue, 3 prérequis manquants, 4 sur batterie (--nuit).

<dossier hors dépôt> reçoit ce qui ne doit pas entrer dans Git : textes des pages légales, DOM, captures, moteur
Opquast. Les résultats versionnés vont dans resultats/<outil>-AAAA-MM-JJ/.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
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
            py + ["scripts/verifier_citations.py", textes]]
        # validation des sorties des lectures IA avant la fusion (sautée tant que le script n'est pas livré)
        + ([py + ["scripts/valider_lectures.py", str(hors)]] if (RACINE / "scripts" / "valider_lectures.py").exists() else []) + [
            py + ["scripts/fusion_scripts.py"],
            py + ["scripts/etat_barometre.py"],
            py + ["scripts/lecture_critique.py"],
            py + ["scripts/generer_suivi.py"],
            py + ["scripts/exporter_csv.py"],
            py + ["scripts/regles_une_source.py", str(hors)]],
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
    jour = time.strftime('%Y-%m-%d')
    journal = RACINE / "resultats" / f"journal-barometre-{jour}.log"
    args = [x for x in sys.argv[1:] if x not in ("--nuit", "--forcer")]
    if "--arreter" not in args and "--continuer" not in args:
        args.append("--continuer")  # la nuit, un échec sur un site ne perd pas le reste du passage
    cmd = bloque + [sys.executable, str(Path(__file__).resolve())] + args
    print(f"Passage de nuit lancé ({' '.join(bloque) or 'sans blocage de veille'}). Journal : {journal}", flush=True)
    with journal.open("a", encoding="utf-8") as j:
        j.write(f"\n===== début {time.strftime('%Y-%m-%d %H:%M:%S')} : {' '.join(cmd)}\n")
        j.flush()
        r = subprocess.run(cmd, cwd=RACINE, stdout=j, stderr=subprocess.STDOUT, env={**os.environ, "BAROMETRE_EVEILLE": "1", "BAROMETRE_DATE": jour})
        j.write(f"===== fin {time.strftime('%Y-%m-%d %H:%M:%S')}, code {r.returncode}\n")
    print(f"Terminé (code {r.returncode}). Voir {journal}")
    return r.returncode


def citer(cmd: list[str]) -> str:
    return " ".join(shlex.quote(c) for c in cmd)


def reprise(a, choix: list[str], echecs: list[dict]) -> str:
    """Commande exacte qui relance le passage à partir de la première étape en échec (echecs non vide)."""
    restant = choix[choix.index(echecs[0]["etape"]):]
    cmd = ["python3", "scripts/barometre.py", "--hors", a.hors]
    cmd += ["--depuis", restant[0]] if restant == ORDRE[ORDRE.index(restant[0]):] else ["--etapes", ",".join(restant)]
    cmd += ["--service", a.service] if a.service else []
    return citer(cmd)


def ecrire_etat(etat: dict) -> Path:
    """État machine du passage, lu par bilan_journal.py et compte_rendu.py (réécrit après chaque commande)."""
    f = RACINE / "resultats" / f"etat-passage-{etat['date']}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")
    return f


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--hors", required=True, help="dossier hors dépôt (textes, DOM, captures, moteur Opquast)")
    ap.add_argument("--etapes", help="étapes à lancer, séparées par des virgules (défaut : toutes)")
    ap.add_argument("--depuis", choices=ORDRE, help="lancer à partir de cette étape")
    ap.add_argument("--service", help="un seul site (nom exact de scripts/ecrans_en_ligne.csv)")
    ap.add_argument("--essai", action="store_true", help="afficher les commandes sans les lancer")
    ap.add_argument("--continuer", action="store_true", help="ne pas s'arrêter quand une commande échoue (défaut avec --nuit)")
    ap.add_argument("--arreter", action="store_true", help="avec --nuit : s'arrêter au premier échec")
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
    choix = [x for x in ORDRE if x in choix]
    continuer = a.continuer and not a.arreter
    etat = {"date": os.environ.get("BAROMETRE_DATE") or time.strftime("%Y-%m-%d"), "debut": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "fin": None, "termine": False, "code": None, "hors": str(hors), "service": a.service, "continuer": continuer,
            "etapes_demandees": choix, "etapes": {e: {"statut": "à faire", "commandes": []} for e in choix},
            "echecs": [], "reprise": None}
    code = 0
    for e in choix:
        print(f"\n=== {e}", flush=True)
        for cmd in plan[e]:
            cmd = resoudre(cmd)
            print("  $", " ".join(f'"{c}"' if " " in c else c for c in cmd), flush=True)
            if a.essai:
                continue
            etat["etapes"][e]["statut"] = "en cours"
            t = time.time()
            r = subprocess.run(cmd, cwd=RACINE)
            nom = Path(cmd[1]).name if len(cmd) > 1 else cmd[0]
            etat["etapes"][e]["commandes"].append({"nom": nom, "commande": citer(cmd), "code": r.returncode, "duree_s": round(time.time() - t)})
            if r.returncode != 0:
                etat["echecs"].append({"etape": e, "nom": nom, "commande": citer(cmd), "code": r.returncode})
                etat["reprise"] = reprise(a, choix, etat["echecs"])
            ecrire_etat(etat)
            if r.returncode != 0 and not continuer:
                print(f"\nÉchec ({r.returncode}) : {' '.join(cmd)}. Corriger puis relancer avec --depuis {e}.", file=sys.stderr)
                code = r.returncode
                break
        if a.essai:
            continue
        etat["etapes"][e]["statut"] = "échec" if any(x["code"] for x in etat["etapes"][e]["commandes"]) else "fait"
        if code:
            break
    if a.essai:
        return 0
    code = code or (1 if etat["echecs"] else 0)
    etat.update(fin=time.strftime("%Y-%m-%dT%H:%M:%S"), termine=True, code=code)
    fichier = ecrire_etat(etat)
    print("\n===== bilan du passage")
    for e, v in etat["etapes"].items():
        for c in v["commandes"]:
            print(f"  {'ok   ' if c['code'] == 0 else 'ÉCHEC'} {e:<11} {c['nom']:<26} {c['duree_s']} s" + (f" (code {c['code']})" if c["code"] else ""))
        if not v["commandes"]:
            print(f"  {'-':<5} {e:<11} {'(non lancée)':<26}")
    print(f"Échecs : {len(etat['echecs'])}")
    for x in etat["echecs"]:
        print(f"  {x['etape']} : {x['commande']} (code {x['code']})")
    if etat["reprise"]:
        print(f"Reprise : {etat['reprise']}")
    print(f"État du passage : {fichier}", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
