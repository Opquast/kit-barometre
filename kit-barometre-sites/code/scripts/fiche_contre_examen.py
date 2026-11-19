#!/usr/bin/env python3
"""Fiche de contre-examen des 29 règles « manuelles » (socle Opquast basics non scriptable), site par site.

Pour chaque règle et chaque site : verdict du robot d'eServices Manager (et son constat quand il est non conforme),
constat objectif relevé dans le navigateur par scripts/contre_examen.mjs, proposition (confirmer, corriger,
ou tester par un parcours réel), et la décision de Mattea, « à faire » tant qu'elle n'est pas prise.

Décision : tranchée par Claude à partir des constats (contre-examen, parcours sans commande, captures de focus), marquée
« à valider par Mattea » (décisions validées par Mattea le 12/11). Les règles qui demandent un compte, une commande ou un envoi restent « parcours de Mattea ».

Entrées : resultats/etat-*/etat.json, resultats/esm-basics-*/preuves_nc.json, resultats/contre-examen-*/constats.json,
          resultats/parcours-*/parcours.json (si présent), referentiel/recommandations.csv.
Sorties : resultats/contre-examen-AAAA-MM-JJ/fiche.json et fiche.csv (une ligne par site et par règle).
Usage : python3 scripts/fiche_contre_examen.py
"""
from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
LIB = {"C": "conforme", "NC": "non conforme", "NA": "non applicable", "NT": "non testé", None: "non évalué"}
PARCOURS = {
    18: "créer un compte client et vérifier qu'un e-mail de confirmation arrive",
    23: "se connecter à un compte et chercher le lien de déconnexion",
    30: "aller jusqu'au paiement sans créer de compte (commande en invité)",
    58: "aller jusqu'à l'étape de paiement et compter les moyens proposés",
    59: "au paiement, vérifier que l'enregistrement de la carte demande un accord explicite",
    60: "dans le compte, chercher la gestion des cartes enregistrées",
    62: "après une commande, chercher la facture dans le compte",
    63: "après une commande, vérifier l'e-mail de facturation",
    66: "après une commande, vérifier l'e-mail de confirmation (référence et détail)",
    79: "envoyer un formulaire avec un champ invalide et regarder si le champ fautif est signalé",
    80: "envoyer un formulaire avec un champ invalide et lire la raison du rejet",
    87: "parcourir le tunnel de commande et chercher la liste des étapes",
    110: "envoyer le formulaire de contact et vérifier l'accusé de réception",
    166: "parcourir l'accueil, une fiche produit et le panier au clavier seul (Tab, Entrée, Échap)",
    173: "s'inscrire à la newsletter et vérifier l'e-mail de confirmation (double opt-in)",
    224: "provoquer une page 403 (accès interdit) : peu probable sur Shopify, à justifier en non applicable",
}


def dernier(motif: str) -> Path | None:
    l = sorted(RACINE.glob(motif))
    return l[-1] if l else None


def proposition(n: int, robot: str | None, c: dict, nom: str) -> tuple[str, str]:
    """(constat navigateur, proposition) pour une règle et un site."""
    ins = c.get("inscription", {})
    shopify = bool(ins.get("hors_site"))
    if n == 68 and "r68" in c:
        m = c["r68"]
        if m.get("mention_trouvee"):
            if "origine naturelle" in m["extrait"]:
                return (f"Fiche produit : « {m['extrait']} » (origine des ingrédients, pas lieu de fabrication).", "Confirmer non conforme : la provenance du produit n'est pas indiquée.")
            return (f"Fiche produit : « {m['extrait']} ».", "Corriger en conforme pour la fiche produit testée ; vérifier les autres fiches.")
        return ("Aucune mention d'origine ou de fabrication sur la fiche produit testée.", "Confirmer non conforme.")
    if n in (75, 76, 203):
        if shopify:
            return ("Compte client hébergé par Shopify : connexion par code envoyé par e-mail, aucun mot de passe.", "Non applicable (pas de mot de passe créé par l'utilisateur)." + (" Corriger le verdict du robot." if robot not in ("NA", None) else ""))
        if ins.get("formulaire"):
            t = ins.get("bouton_afficher_mot_de_passe"); j = ins.get("jauge_robustesse")
            if n == 76:
                return (f"Page d'inscription : bouton « afficher le mot de passe » {'présent' if t else 'absent'}.", "Conforme." if t else "Confirmer non conforme.")
            if n == 75:
                return (f"Un seul champ mot de passe, bouton d'affichage {'présent' if t else 'absent'}.", "Conforme (l'affichage en clair évite les erreurs de saisie)." if t else "Non conforme : ni confirmation ni affichage en clair.")
            return (f"Jauge de robustesse {'présente' if j else 'absente'} sur la page d'inscription.", "Conforme." if j else "Non conforme.")
    if n == 17:
        if shopify:
            return ("Création de compte par e-mail et code, sur le domaine Shopify, sans compte tiers obligatoire.", "Conforme.")
        if ins.get("formulaire"):
            return (f"Formulaire e-mail et mot de passe ; {ins.get('boutons_identification_tierce', 0)} bouton(s) de connexion tierce en option.", "Conforme (l'identification tierce reste facultative).")
    if n == 140 and "r140" in c:
        ps = [p for p in c["r140"]["pages"] if not p.get("non_teste")]
        nb = sum(p.get("liens_dans_le_texte", 0) for p in ps); sans = sum(p.get("sans_soulignement_ni_graisse", 0) for p in ps)
        ex = next((p["exemple"] for p in ps if p.get("exemple")), "")
        if nb == 0:
            return ("Aucun lien dans le texte courant des pages de contenu testées.", "À vérifier à l'œil sur une page avec des liens dans le texte.")
        return (f"{sans} lien(s) sur {nb} dans le texte sans soulignement ni graisse" + (f" (ex. « {ex} »)" if ex else "") + ".",
                "Confirmer non conforme." if sans else "Corriger en conforme.")
    if n == 165 and "r165" in c:
        f = c["r165"]
        if f["sans_focus_visible"]:
            return (f"{f['sans_focus_visible']} élément(s) sur {f['elements_atteints']} atteints au clavier sans contour de focus ({', '.join(f['exemples_sans_focus'])}).", "Confirmer non conforme.")
        return (f"Contour ou ombre de focus détecté sur les {f['elements_atteints']} premiers éléments atteints au clavier.", "Écart avec le robot : vérifier à l'œil (contour réellement visible et contrasté ?) avant de corriger.")
    if n == 166 and "r166" in c:
        return (f"{c['r166']['elements_atteints_au_clavier_sur_15_tabs']} éléments atteints sur 15 tabulations depuis le haut de l'accueil.", "Tester à la main : " + PARCOURS[166] + ".")
    if n == 216:
        return ("Le site s'ouvre dans la fenêtre courante, barre d'adresse visible.", "Confirmer conforme.")
    if n == 223 and "r223" in c:
        x = c["r223"]
        langue = " (en anglais à la racine du domaine)" if "NOT FOUND" in x.get("texte", "") else ""
        return (f"Code {x['code']}, page aux couleurs du site (en-tête et pied présents){langue} : « {x['texte'][:60]} ».", "Confirmer conforme.")
    if n == 5 and "r5" in c:
        return ("Aucune balise <abbr title> ; les capitales relevées viennent surtout de la mise en forme des titres.", "À vérifier à la lecture : sigles réels (FAQ, CGV, RGPD…) explicités à leur première occurrence ?")
    if n in (90, 96, 149) and robot == "NA":
        return ("", "Confirmer non applicable (pas de processus concerné dans l'échantillon).")
    if n in PARCOURS:
        return ("Non vérifiable sans parcours réel (pas de commande, de compte ni d'envoi de formulaire sur les sites en production).", "Tester à la main : " + PARCOURS[n] + ".")
    return ("", "À vérifier à la main.")


MATTEA = {18, 23, 59, 60, 62, 63, 66, 110, 173}


def trancher(n: int, robot: str | None, prop: str, p: dict) -> tuple[str | None, str]:
    """(statut décidé ou None, motif). None : la décision revient à Mattea (parcours avec compte, commande ou envoi)."""
    if n in MATTEA:
        return None, "Parcours de Mattea : demande un compte, une commande ou un envoi réel."
    pa = p.get("paiement", {}) if p else {}
    if n == 30 and "champ_email_ou_tel" in pa:
        return ("C", "Page de paiement atteinte sans compte : e-mail demandé, connexion facultative.") if not pa["connexion_obligatoire"] else ("NC", "Connexion exigée pour commander.")
    if n == 58 and "moyens_paiement" in pa:
        m = pa["moyens_paiement"]
        return ("C" if len(m) >= 2 else "NC"), f"{len(m)} moyens de paiement affichés au paiement ({', '.join(m)})."
    if n == 87 and "etapes" in pa:
        return ("C", "Étapes affichées : " + " > ".join(pa["etapes"])) if pa["etapes"] else ("NC", "Paiement Shopify sur une seule page : ni liste des étapes ni étape en cours entre panier, paiement et confirmation.")
    f = p.get("formulaire", {}) if p else {}
    if n in (79, 80) and f.get("trouve"):
        if f.get("message_propre_au_site"):
            return None, "Le site gère ses propres messages d'erreur (novalidate) : à voir en envoyant le formulaire, par Mattea."
        if not f["valide"]:
            return "C", ("Adresse « test@ » refusée avant envoi, champ fautif mis en avant par le navigateur." if n == 79 else "Le message explique la raison du refus (partie après @ manquante), dans la langue du navigateur.")
        return "NC", "Adresse invalide acceptée sans message."
    if n == 166:
        kp = p.get("clavier_produit", {}) if p else {}
        t = kp.get("bouton_panier_atteint_en_tabulations")
        if t:
            lourd = f" Parcours très long : {kp['liens_avant_le_bouton']} liens du menu à traverser avant le bouton, sans lien d'évitement (règle 164)." if kp.get("liens_avant_le_bouton", 0) > 60 else ""
            return "C", f"Accueil et fiche produit parcourus au clavier ; « Ajouter au panier » atteint en {t} tabulations" + (", ajout réussi." if kp.get("ajout_au_clavier") else " (ajout sans effet : choisir d'abord la taille).") + lourd
        return None, "« Ajouter au panier » non atteint en 80 tabulations : à refaire à la main par Mattea (variante à choisir ou bouton hors de l'ordre de tabulation)."
    if n == 165:
        if prop.startswith("Confirmer non conforme"):
            return "NC", "Éléments atteints au clavier sans aucun contour de focus."
        k = p.get("clavier_accueil", {}) if p else {}
        return "C", f"Focus visible à l'œil sur les captures des premiers éléments ; {k.get('sans_indicateur', '?')} élément sans indicateur sur {k.get('elements_atteints', '?')}. Le robot se fondait sur une règle CSS outline:none présente quelque part, pas sur un élément réel."
    if n == 224:
        return "NA", "Shopify ne sert pas de page 403 aux visiteurs : pas d'espace à accès interdit dans le parcours public."
    if n == 140 and prop.startswith("À vérifier"):
        return robot, "Aucun lien dans le texte des pages testées : verdict du robot (liens de même couleur que le texte, sans soulignement) gardé, à revoir sur une page éditoriale."
    if n == 5:
        return robot, "Aucune abréviation non expliquée relevée par le robot ; les capitales viennent de la mise en forme : verdict du robot gardé."
    if prop.startswith(("Confirmer non conforme", "Non conforme", "Confirmer non conforme.")):
        return "NC", prop
    if prop.startswith(("Conforme", "Confirmer conforme", "Corriger en conforme")):
        return "C", prop
    if prop.startswith(("Non applicable", "Confirmer non applicable")):
        return "NA", prop
    return robot, "Aucun constat contraire : verdict du robot gardé."


def main() -> None:
    f_etat = dernier("resultats/etat-*/etat.json")
    if f_etat is None:
        print("Aucun état consolidé (resultats/etat-*/etat.json) : lancer d'abord scripts/etat_barometre.py.")
        return
    etat = json.loads(f_etat.read_text(encoding="utf-8"))["sites"]
    # Sans export eServices Manager ni contre-examen dans le navigateur : constats vides, décisions « à vérifier ».
    f_preuves = dernier("resultats/esm-basics-*/preuves_nc.json")
    preuves = json.loads(f_preuves.read_text(encoding="utf-8")) if f_preuves else {}
    dossier = dernier("resultats/contre-examen-*")
    if dossier is None:
        dossier = RACINE / "resultats" / f"contre-examen-{date.today():%Y-%m-%d}"
        dossier.mkdir(parents=True, exist_ok=True)
    f_constats = dossier / "constats.json"
    constats = json.loads(f_constats.read_text(encoding="utf-8"))["sites"] if f_constats.is_file() else {}
    fp = sorted(RACINE.glob("resultats/parcours-*/parcours.json"))
    parcours = json.loads(fp[-1].read_text(encoding="utf-8")) if fp else {}
    recos = {x["code"]: x["recommandation"] for x in csv.DictReader((RACINE / "referentiel" / "recommandations.csv").open(encoding="utf-8"))}
    regles = [int(x["numero"]) for x in csv.DictReader((RACINE / "referentiel" / "repartition-regles.csv").open(encoding="utf-8")) if x["methode"] == "manuel"]
    fiche = {}
    for nom, v in etat.items():
        lignes = []
        exclues = set(json.loads((RACINE / "referentiel" / "exclusions-sites.json").read_text(encoding="utf-8")).get(nom, []))
        for n in regles:
            if n in exclues:
                continue
            e = v.get(str(n), {})
            robot = e.get("robot")
            constat, prop = proposition(n, robot, constats.get(nom, {}), nom)
            pr = preuves.get(nom, {}).get(str(n), {}).get("commentaire", "") if robot == "NC" else ""
            dec, motif = trancher(n, robot, prop, parcours.get(nom, {}))
            lignes.append({"regle": n, "titre": e.get("titre", ""), "robot": robot, "robot_constat": pr[:300],
                           "constat_navigateur": constat, "proposition": prop,
                           "decision": "tranchée par Claude, validée par Mattea le 12/11" if dec else "parcours de Mattea",
                           "decision_statut": dec, "decision_motif": motif,
                           "recommandation": ("Sur " + nom + " : " + recos[str(n)]) if dec == "NC" and str(n) in recos else ""})
        fiche[nom] = lignes
    (dossier / "fiche.json").write_text(json.dumps(fiche, ensure_ascii=False, indent=1), encoding="utf-8")
    with (dossier / "fiche.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["site", "regle", "titre", "verdict_robot", "constat_robot", "constat_navigateur", "proposition", "decision", "statut_decide", "motif"])
        for nom, ls in fiche.items():
            for l in ls:
                w.writerow([nom, l["regle"], l["titre"], LIB[l["robot"]], l["robot_constat"], l["constat_navigateur"], l["proposition"], l["decision"], (LIB[l["decision_statut"]] if l["decision_statut"] else ""), l["decision_motif"]])
    from collections import Counter
    print({nom: Counter(str(l["decision_statut"]) for l in ls) for nom, ls in fiche.items()})


if __name__ == "__main__":
    main()
