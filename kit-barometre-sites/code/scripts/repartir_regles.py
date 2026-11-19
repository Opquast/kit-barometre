#!/usr/bin/env python3
"""Répartit les 245 règles Opquast V5 entre l'IA (eServices Manager) et nos contrôles sans IA.

Principe de coût : l'IA (probabiliste, payante) passe par un seul audit, le robot d'eServices Manager sur la
checklist native « Opquast basics » (65 règles, lancé le 12/11/2026). Le robot sur les 20 règles « IA » choisies
au départ n'est pas lancé (décision du 12/11/2026) : celles qui sont dans le socle basics restent évaluées par le
robot, les autres sont écartées. Le reste est fait de notre côté sans IA :
  - déterministe réseau : scripts/controles_reseau.py (en-têtes, HTTPS, robots.txt…) ;
  - déterministe page   : scripts/controles_page.js dans le navigateur (lecture du code de la page)
                          et axe-core pour l'accessibilité ;
  - manuel              : les 20 règles du socle basics (29 moins 9 retirées le 12/11) qui ne se scriptent pas : verdict du robot puis
                          contre-examen par la personne responsable (referentiel/parc.json) ;
  - écartée             : les autres règles qui demanderaient un jugement visuel ou un parcours réel
                          (commande, compte, formulaire, e-mail reçu) : hors périmètre pour l'instant
                          (décision du 12/11/2026).

Sortie : referentiel/repartition-regles.csv
Usage  : python3 scripts/repartir_regles.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import parc

RACINE = Path(__file__).resolve().parent.parent

# Les 20 règles confiées à l'IA d'eServices Manager, avec la raison du choix.
IA = {
    16: "Lire la politique de confidentialité et juger si la procédure d'accès et de rectification est vraiment décrite (RGPD).",
    29: "Juger si la bannière et la page cookies expliquent l'objectif et les limites du refus (recommandation CNIL).",
    39: "Juger si la fiche produit donne la nature et les caractéristiques chiffrées utiles à l'achat.",
    40: "Repérer les promotions et vérifier que période et conditions sont indiquées (prix barrés, Omnibus).",
    47: "Trouver et comprendre la zone de livraison dans des textes rédigés librement.",
    51: "Trouver l'adresse et les conditions de retour dans les CGV ou la FAQ.",
    56: "Juger si les prix affichés précisent taxes et suppléments.",
    65: "Juger si un produit indisponible est différencié à la fois visuellement et par le texte.",
    71: "Juger si chaque étiquette indique clairement le caractère obligatoire (astérisque expliqué, mention).",
    72: "Juger si le format attendu est indiqué là où il est nécessaire (date, téléphone, code postal).",
    99: "Juger si la page d'accueil fait comprendre ce que le site propose.",
    103: "Juger si le titre de chaque page décrit vraiment son contenu.",
    117: "Juger si l'alternative d'une image-lien décrit sa destination.",
    118: "Juger si l'alternative d'une image informative transmet la même information.",
    137: "Juger si le libellé de chaque lien décrit sa fonction ou sa destination.",
    159: "Juger si les icônes de navigation (panier, compte, recherche, menu) ont une légende explicite.",
    179: "Trouver si la fréquence d'envoi de la newsletter est annoncée avant l'inscription.",
    181: "Repérer visuellement une information donnée seulement par la couleur.",
    184: "Repérer un contenu désigné seulement par sa forme ou sa position (« cliquez à droite »).",
    187: "Repérer visuellement des textes remplacés par des images (bannières, visuels promotionnels).",
}

# Règles réseau mesurées par scripts/controles_reseau.py (les 6 dernières sont à ajouter au script).
RESEAU = {197, 198, 199, 200, 206, 207, 210, 211, 212, 213, 214, 217, 218, 219, 220, 222, 226, 227, 228}
RESEAU_A_AJOUTER = {25, 135, 209, 221, 229, 230}
RESEAU = RESEAU | RESEAU_A_AJOUTER

# Règles vérifiées par scripts/controles_page.js dans le navigateur, plus 3 règles couvertes par axe-core.
PAGE = {3, 13, 15, 27, 28, 46, 69, 92, 95, 97, 98, 102, 104, 105, 107, 116, 119, 120, 121, 122, 124, 125, 128, 130,
        136, 145, 146, 147, 148, 152, 155, 156, 157, 164, 168, 169, 170, 171, 186, 190, 191, 193, 194, 195, 232, 233,
        234, 236, 237, 238, 239, 240, 242, 243}
AXE = {182, 185, 244}
PAGE = PAGE | AXE

OUTILS = {"IA": "eServices Manager, robot sur Opquast basics", "manuel": "{responsable}, contre-examen du verdict du robot (Opquast basics)", "réseau": "scripts/controles_reseau.py",
          "page": "scripts/controles_page.js et axe-core", "écartée": "hors périmètre pour l'instant",
          "relevé": "scripts/releve_regles.mjs et regles_releve.py (Claude, à valider)"}


def verifier(condition: bool, message: str) -> None:
    """Contrôle de cohérence du référentiel, actif même avec python -O (contrairement à assert)."""
    if not condition:
        raise SystemExit(f"Répartition incohérente : {message}")


def main() -> None:
    regles = json.loads((RACINE / "referentiel" / "opquast-checklist-v5.json").read_text(encoding="utf-8"))
    verifier(len(IA) == 20, f"{len(IA)} règles IA au lieu de 20")
    verifier(not (set(IA) & (RESEAU | PAGE)), f"règles IA aussi en script : {set(IA) & (RESEAU | PAGE)}")
    verifier(not (RESEAU & PAGE), f"règles à la fois réseau et page : {RESEAU & PAGE}")
    BASICS = {r["number"] for r in regles if "Basics" in " ".join(r["metadata"].get("Tags", []))}
    verifier(len(BASICS) == 65, f"{len(BASICS)} règles Basics au lieu de 65")
    # Retirées le 12/11 (décision de la personne responsable) : impossibles à tester sans créer de compte client, passer une commande payée
    # ou envoyer un vrai message ou une vraie inscription sur les sites des clients en production.
    NON_TESTABLES = {18, 23, 59, 60, 62, 63, 66, 110, 173}
    # Tranchées par le relevé navigateur du 12/11 (scripts/releve_regles.mjs puis regles_releve.py), sur au moins un site
    RELEVE = set(json.loads((RACINE / "resultats" / "releve-2026-11-12" / "decisions.json").read_text(encoding="utf-8")) and
                 {int(k) for s_ in json.loads((RACINE / "resultats" / "releve-2026-11-12" / "decisions.json").read_text(encoding="utf-8")).values()
                  for k, v in s_.items() if v[0] in ("C", "NC", "NA")}) | {33}  # 33 : parcours panier (scripts/parcours.mjs)
    qui = parc.responsable()
    lignes, compte = [], {}
    for r in regles:
        n = r["number"]
        if n in RELEVE and n not in BASICS and n not in NON_TESTABLES:
            # Cohérence (12/11) : une règle tranchée par le relevé est mesurée, même si elle était prévue pour l'IA
            m, raison = "relevé", (f"Tranchée par le parcours panier (case précochée) et le relevé navigateur, par Claude, à valider par {qui}." if n == 33 else
                                   f"Tranchée par le relevé navigateur (mesure dans la page ou lecture des pages légales), par Claude, à valider par {qui}.")
        elif n in IA and n in BASICS:
            m, raison = "IA", IA[n] + " Évaluée par le robot d'eServices Manager dans l'audit Opquast basics."
        elif n in IA:
            m, raison = "écartée", "Choisie au départ pour l'IA, mais le robot sur les 20 règles n'est pas lancé et elle n'est pas dans le socle basics."
        elif n in RESEAU:
            m, raison = "réseau", ("Se mesure sur les échanges HTTP : à ajouter au script réseau." if n in RESEAU_A_AJOUTER
                                   else "Se mesure sur les échanges HTTP ou le DNS : même entrée, même résultat.")
        elif n in PAGE:
            m, raison = "page", ("Couverte par axe-core (WCAG)." if n in AXE else "Se vérifie en lisant le code de la page rendue (balises, attributs, styles).")
        elif n in NON_TESTABLES:
            m, raison = "écartée", "Retirée le 12/11 : non testable sans compte client, commande payée ou envoi réel sur un site client en production."
        elif n in BASICS:
            m, raison = "manuel", f"Socle Opquast basics, non scriptable : verdict du robot d'eServices Manager, contre-examiné par {qui}."
        else:
            m, raison = "écartée", "Écartée pour l'instant : demanderait un jugement visuel ou un parcours réel (commande, compte, formulaire, e-mail reçu)."
        compte[m] = compte.get(m, 0) + 1
        lignes.append([n, ", ".join(r["metadata"].get("Thématiques", [])), r["description"]["fr"], m, OUTILS[m].format(responsable=qui), raison])
    with (RACINE / "referentiel" / "repartition-regles.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["numero", "theme", "regle", "methode", "outil", "raison"])
        w.writerows(lignes)
    print(compte, sum(compte.values()))


if __name__ == "__main__":
    main()
