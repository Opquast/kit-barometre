"""Tests de etat_barometre.py et fiche_contre_examen.py."""

from __future__ import annotations

import csv
from datetime import date

import pytest

import etat_barometre as eb
import fiche_contre_examen as fce
import parc
from aide_parc import PARC_ORIGINE, poser_parc
from conftest import ecrire_json, lire_json


# --- etat_barometre ---------------------------------------------------------

def test_combine_et_court():
    assert eb.combine(["C", "NC"]) == "NC"
    assert eb.combine(["X"]) == "NT"
    assert eb.court("a  b\nc") == "a b c"
    assert eb.court("mot " * 10, 12) == "mot mot…"


def test_dernier(racine):
    r = racine(eb)
    assert eb.dernier("resultats/rien-*") is None
    (r / "resultats/esm-scripts-2026-11-12").mkdir()
    (r / "resultats/esm-scripts-2026-11-13").mkdir()
    assert eb.dernier("resultats/esm-scripts-*").name == "esm-scripts-2026-11-13"


def preparer_etat(r, monkeypatch, emails=True, sites=("A", "C"), autres=()):
    monkeypatch.setattr(parc, "RACINE", r)
    ecrire_json(r / "referentiel/parc.json", {"responsable": "Mattea", "sites": [s for s in PARC_ORIGINE["sites"] if s["nom"][-1] in sites]})
    ecrire_json(r / "resultats/esm-scripts-2026-11-12/WEB-BOUTIQUEA.json", [
        {"titre": "Accueil", "resultats": {"1": ["NC", "défaut 1"], "3": ["C", "ok 3"], "4": ["NA", "na 4"],
                                           "8": ["NC", "défaut 8"], "10": ["C", "ok 10"]}},
        {"titre": "Panier", "resultats": {"3": ["C", "ok 3 bis"]}},
    ])
    regles = {
        "1": {"sites": {"Boutique A": "non conforme"}, "comptes_pages": {"Boutique A": {"non conforme": 2}}},
        "2": {"sites": {"Boutique A": "non conforme"}, "comptes_pages": {}},
        "3": {"sites": {"Boutique A": "conforme"}, "comptes_pages": {"Boutique A": {"conforme": 4}}},
        "5": {"sites": {"Boutique A": "indéterminé"}, "comptes_pages": {"Boutique A": {"indéterminé": 1, "non testé": 2}}},
        "6": {"sites": {}, "comptes_pages": {}},
        "8": {"sites": {"Boutique A": "conforme"}, "comptes_pages": {}},
        "9": {"sites": {"Boutique A": "conforme"}, "comptes_pages": {"Boutique A": {"conforme": 1}}},
        "10": {"sites": {"Boutique A": "non applicable"}, "comptes_pages": {}},
    }
    ecrire_json(r / "resultats/esm-basics-2026-11-12/resultats.json", {"regles": regles})
    ecrire_json(r / "resultats/esm-basics-2026-11-12/preuves_nc.json",
                {"Boutique A": {"1": {"pages": ["Accueil", "Produit"], "commentaire": "robot 1"}}})
    (r / "referentiel/recommandations.csv").write_text(
        "code,niveau,recommandation\n1,thème,Reco 1\n2,thème,Reco 2\n5,thème,Reco 5\nE1,thème,Reco E1\nE3,thème,Reco E3\n", encoding="utf-8")
    if emails:
        (r / "referentiel/checklist-email.csv").write_text(
            "id,critere,theme\nE1,Objet,Contenu\nE2,Lien,Liens\nE3,Pied,Contenu\nE4,Alt,Images\nE5,Rien,Autre\nE6,Vide,Autre\n", encoding="utf-8")
        (r / "resultats/email-2026-11-12").mkdir()
        lignes = [("E1", "BOUTIQUEC-EM-BIENVENUE", "non conforme"), ("E1", "BOUTIQUEC-EM-PANIER", "conforme"),
                  ("E2", "BOUTIQUEC-EM-BIENVENUE", "conforme"), ("E3", "BOUTIQUEC-EM-BIENVENUE", "indéterminé"),
                  ("E4", "BOUTIQUEC-EM-BIENVENUE", "non applicable"), ("E5", "BOUTIQUEC-EM-BIENVENUE", "non testé"),
                  ("E6", "BOUTIQUEC-EM-BIENVENUE", "autre")] + list(autres)
        with (r / "resultats/email-2026-11-12/resultats.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["critere", "ecran_code", "statut", "methode", "justification", "preuve"])
            for c, e, s in lignes:
                w.writerow([c, e, s, "IA", "parce que", "capture"])


def test_etat_barometre(racine, monkeypatch, capsys):
    r = racine(eb)
    preparer_etat(r, monkeypatch)
    eb.main()
    etat = lire_json(r / "resultats" / f"etat-{date.today():%Y-%m-%d}" / "etat.json")
    s = etat["sites"]["Boutique A"]
    assert s["1"]["statut"] == "NC" and s["1"]["pages_nc"] == ["Accueil", "Produit"]
    assert s["1"]["determinant"] == ["Scripts, Accueil : défaut 1", "Robot, Accueil : robot 1"]
    assert s["1"]["recommandation"] == "Sur Boutique A (Accueil, Produit) : Reco 1"
    assert [x["statut"] for x in s["1"]["sources"]] == ["NC", "NC"]
    assert s["2"]["statut"] == "NC" and s["2"]["determinant"] == [] and s["2"]["recommandation"] == "Sur Boutique A : Reco 2"
    assert s["3"]["statut"] == "C" and s["3"]["determinant"][0].startswith("Scripts, 2 page(s) conformes")
    assert s["3"]["determinant"][1] == "Robot : conforme sur 4 page(s) de l'échantillon."
    assert s["4"]["statut"] == "NA" and s["4"]["robot"] is None and len(s["4"]["determinant"]) == 1
    assert s["5"]["statut"] == "NT" and "1 page(s) indéterminée(s), 2 non testée(s)" in s["5"]["determinant"][0]
    assert s["5"]["recommandation"].startswith("Sur Boutique A, à vérifier")
    assert "aucune page testée" in s["6"]["determinant"][0] and s["6"]["recommandation"] == ""
    assert s["8"]["statut"] == "NC" and s["8"]["determinant"] == ["Scripts, Accueil : défaut 8"]
    assert s["9"]["determinant"] == ["Robot : conforme sur 1 page(s) de l'échantillon."]
    assert s["10"]["statut"] == "C" and len(s["10"]["determinant"]) == 1
    e = etat["emails"]["Klaviyo Boutique C"]
    assert e["E1"]["statut"] == "NC" and e["E1"]["recommandation"] == "Sur Klaviyo Boutique C (bienvenue) : Reco E1"
    assert e["E2"]["statut"] == "C" and e["E2"]["recommandation"] == ""
    assert e["E3"]["statut"] == "I" and e["E3"]["recommandation"].startswith("Sur Klaviyo Boutique C, à vérifier")
    assert e["E4"]["statut"] == "NA"
    assert e["E5"]["statut"] == "NT" and e["E5"]["recommandation"] == ""
    assert e["E6"]["statut"] == "NT" and e["E6"]["ecrans"]["BOUTIQUEC-EM-BIENVENUE"][0] == "autre"
    assert "recommandations manquantes : ['8']" in capsys.readouterr().out


def test_etat_barometre_sans_emails(racine, monkeypatch):
    r = racine(eb)
    preparer_etat(r, monkeypatch, emails=False)
    eb.main()
    assert lire_json(r / "resultats" / f"etat-{date.today():%Y-%m-%d}" / "etat.json")["emails"] == {}


def test_etat_barometre_emails_par_compte(racine, monkeypatch):
    """Écrans répartis par préfixe ; un écran sans préfixe connu va au premier compte du parc."""
    r = racine(eb)
    preparer_etat(r, monkeypatch, sites=("A", "C", "F"), autres=[("E2", "MAJ-EM-BIENVENUE", "non conforme"), ("E2", "AUTRE-EM-X", "conforme")])
    eb.main()
    emails = lire_json(r / "resultats" / f"etat-{date.today():%Y-%m-%d}" / "etat.json")["emails"]
    assert set(emails) == {"Klaviyo Boutique C", "Klaviyo Boutique F"}
    assert emails["Klaviyo Boutique F"]["E2"]["recommandation"].startswith("Sur Klaviyo Boutique F (bienvenue)")
    assert set(emails["Klaviyo Boutique C"]["E2"]["ecrans"]) == {"BOUTIQUEC-EM-BIENVENUE", "AUTRE-EM-X"}


def test_etat_barometre_emails_sans_compte(racine, monkeypatch):
    """Parc sans compte e-mail : le fichier des e-mails est ignoré."""
    r = racine(eb)
    preparer_etat(r, monkeypatch, sites=("A",))
    eb.main()
    etat = lire_json(r / "resultats" / f"etat-{date.today():%Y-%m-%d}" / "etat.json")
    assert etat["emails"] == {} and list(etat["sites"]) == ["Boutique A"]


# --- fiche_contre_examen : proposition --------------------------------------

SHOP = {"inscription": {"hors_site": True}}


def form(**k):
    return {"inscription": {"formulaire": True, **k}}


@pytest.mark.parametrize("n, robot, c, constat, prop", [
    (68, "NC", {"r68": {"mention_trouvee": True, "extrait": "ingrédients d'origine naturelle"}}, "origine des ingrédients", "Confirmer non conforme"),
    (68, "NC", {"r68": {"mention_trouvee": True, "extrait": "Fabriqué en France"}}, "Fabriqué en France", "Corriger en conforme"),
    (68, "NC", {"r68": {"mention_trouvee": False}}, "Aucune mention", "Confirmer non conforme."),
    (68, "NC", {}, "", "À vérifier à la main."),
    (75, "NA", SHOP, "Shopify", "Non applicable (pas de mot de passe créé par l'utilisateur)."),
    (76, "C", SHOP, "Shopify", "Non applicable (pas de mot de passe créé par l'utilisateur). Corriger le verdict du robot."),
    (203, None, SHOP, "Shopify", "Non applicable (pas de mot de passe créé par l'utilisateur)."),
    (76, "C", form(bouton_afficher_mot_de_passe=True), "présent", "Conforme."),
    (76, "C", form(), "absent", "Confirmer non conforme."),
    (75, "C", form(bouton_afficher_mot_de_passe=True), "présent", "Conforme (l'affichage"),
    (75, "C", form(), "absent", "Non conforme : ni confirmation"),
    (203, "C", form(jauge_robustesse=True), "présente", "Conforme."),
    (203, "C", form(), "absente", "Non conforme."),
    (75, "C", {}, "", "À vérifier à la main."),
    (17, "C", SHOP, "domaine Shopify", "Conforme."),
    (17, "C", form(boutons_identification_tierce=2), "2 bouton(s)", "Conforme (l'identification"),
    (17, "C", {}, "", "À vérifier à la main."),
    (140, "NC", {"r140": {"pages": [{"non_teste": True, "liens_dans_le_texte": 9}, {"liens_dans_le_texte": 0}]}}, "Aucun lien", "À vérifier à l'œil"),
    (140, "NC", {"r140": {"pages": [{"liens_dans_le_texte": 3, "sans_soulignement_ni_graisse": 2, "exemple": "ici"}]}}, "(ex. « ici »)", "Confirmer non conforme."),
    (140, "NC", {"r140": {"pages": [{"liens_dans_le_texte": 3, "sans_soulignement_ni_graisse": 0}]}}, "0 lien(s) sur 3 dans le texte sans soulignement ni graisse.", "Corriger en conforme."),
    (165, "NC", {"r165": {"sans_focus_visible": 2, "elements_atteints": 10, "exemples_sans_focus": ["a", "b"]}}, "(a, b)", "Confirmer non conforme."),
    (165, "NC", {"r165": {"sans_focus_visible": 0, "elements_atteints": 10}}, "les 10 premiers", "Écart avec le robot"),
    (166, "C", {"r166": {"elements_atteints_au_clavier_sur_15_tabs": 12}}, "12 éléments", "Tester à la main : parcourir l'accueil"),
    (216, "C", {}, "fenêtre courante", "Confirmer conforme."),
    (223, "C", {"r223": {"code": 404, "texte": "404 NOT FOUND"}}, "en anglais", "Confirmer conforme."),
    (223, "C", {"r223": {"code": 404, "texte": "Page introuvable"}}, "« Page introuvable »", "Confirmer conforme."),
    (5, "C", {"r5": {}}, "<abbr title>", "À vérifier à la lecture"),
    (90, "NA", {}, "", "Confirmer non applicable"),
    (90, "C", {}, "", "À vérifier à la main."),
    (18, "NT", {}, "Non vérifiable sans parcours réel", "Tester à la main : créer un compte"),
    (999, None, {}, "", "À vérifier à la main."),
])
def test_proposition(n, robot, c, constat, prop):
    obtenu_constat, obtenu_prop = fce.proposition(n, robot, c, "Boutique A")
    assert constat in obtenu_constat
    assert obtenu_prop.startswith(prop)


# --- fiche_contre_examen : trancher -----------------------------------------

@pytest.mark.parametrize("n, robot, prop, p, statut, motif", [
    (18, "NC", "", {}, None, "Parcours de Mattea"),
    (30, "C", "", {"paiement": {"champ_email_ou_tel": True, "connexion_obligatoire": False}}, "C", "Page de paiement atteinte"),
    (30, "C", "", {"paiement": {"champ_email_ou_tel": True, "connexion_obligatoire": True}}, "NC", "Connexion exigée"),
    (30, "C", "x", None, "C", "Aucun constat contraire"),
    (58, "C", "", {"paiement": {"moyens_paiement": ["CB", "PayPal"]}}, "C", "2 moyens de paiement affichés au paiement (CB, PayPal)."),
    (58, "C", "", {"paiement": {"moyens_paiement": ["CB"]}}, "NC", "1 moyens"),
    (87, "C", "", {"paiement": {"etapes": ["Panier", "Paiement"]}}, "C", "Étapes affichées : Panier > Paiement"),
    (87, "C", "", {"paiement": {"etapes": []}}, "NC", "Paiement Shopify sur une seule page"),
    (79, "C", "", {"formulaire": {"trouve": True, "message_propre_au_site": True}}, None, "Le site gère ses propres messages"),
    (79, "C", "", {"formulaire": {"trouve": True, "valide": False}}, "C", "Adresse « test@ » refusée"),
    (80, "C", "", {"formulaire": {"trouve": True, "valide": False}}, "C", "Le message explique"),
    (80, "C", "", {"formulaire": {"trouve": True, "valide": True}}, "NC", "Adresse invalide acceptée"),
    (79, "C", "z", {"formulaire": {"trouve": False}}, "C", "Aucun constat contraire"),
    (166, "C", "", {"clavier_produit": {"bouton_panier_atteint_en_tabulations": 30, "liens_avant_le_bouton": 70, "ajout_au_clavier": True}}, "C", "ajout réussi. Parcours très long : 70 liens"),
    (166, "C", "", {"clavier_produit": {"bouton_panier_atteint_en_tabulations": 8}}, "C", "(ajout sans effet"),
    (166, "C", "", None, None, "« Ajouter au panier » non atteint"),
    (165, "NC", "Confirmer non conforme.", None, "NC", "Éléments atteints au clavier"),
    (165, "NC", "Écart", {"clavier_accueil": {"sans_indicateur": 0, "elements_atteints": 10}}, "C", "0 élément sans indicateur sur 10"),
    (165, "NC", "Écart", None, "C", "? élément sans indicateur sur ?"),
    (224, "NC", "", None, "NA", "Shopify ne sert pas de page 403"),
    (140, "NC", "À vérifier à l'œil", None, "NC", "Aucun lien dans le texte"),
    (140, "NC", "Corriger en conforme.", None, "C", "Corriger en conforme."),
    (5, "C", "", None, "C", "Aucune abréviation"),
    (1, "C", "Non conforme : x", None, "NC", "Non conforme : x"),
    (1, "NC", "Confirmer conforme.", None, "C", "Confirmer conforme."),
    (1, "C", "Confirmer non applicable", None, "NA", "Confirmer non applicable"),
    (1, "NT", "Tester à la main", None, "NT", "Aucun constat contraire"),
])
def test_trancher(racine, n, robot, prop, p, statut, motif):
    poser_parc(racine)
    obtenu_statut, obtenu_motif = fce.trancher(n, robot, prop, p)
    assert obtenu_statut == statut
    assert motif in obtenu_motif


# --- fiche_contre_examen : main ---------------------------------------------

@pytest.mark.parametrize("avec_parcours", [True, False])
def test_fiche_main(racine, capsys, avec_parcours):
    r = poser_parc(racine, fce)
    ecrire_json(r / "resultats/etat-2026-11-12/etat.json", {"sites": {"Boutique A": {
        "216": {"robot": "NC", "titre": "Fenêtre"}, "18": {"robot": "NT", "titre": "Compte"},
        "140": {"robot": "C", "titre": "Liens"}}}})
    ecrire_json(r / "resultats/esm-basics-2026-11-12/preuves_nc.json", {"Boutique A": {"216": {"commentaire": "robot dit non"}}})
    ecrire_json(r / "resultats/contre-examen-2026-11-12/constats.json", {"sites": {"Boutique A": {
        "r140": {"pages": [{"liens_dans_le_texte": 2, "sans_soulignement_ni_graisse": 2}]}}}})
    if avec_parcours:
        ecrire_json(r / "resultats/parcours-2026-11-12/parcours.json", {"Boutique A": {}})
    (r / "referentiel/repartition-regles.csv").write_text(
        "numero,methode\n216,manuel\n18,manuel\n140,manuel\n17,manuel\n1,réseau\n", encoding="utf-8")
    (r / "referentiel/recommandations.csv").write_text("code,niveau,recommandation\n140,thème,Souligner les liens\n", encoding="utf-8")
    ecrire_json(r / "referentiel/exclusions-sites.json", {"Boutique A": [17]})
    fce.main()
    dossier = r / "resultats/contre-examen-2026-11-12"
    fiche = lire_json(dossier / "fiche.json")["Boutique A"]
    par_regle = {l["regle"]: l for l in fiche}
    assert set(par_regle) == {216, 18, 140}
    assert par_regle[216]["robot_constat"] == "robot dit non" and par_regle[216]["decision_statut"] == "C"
    assert par_regle[216]["decision"] == "tranchée par Claude, à valider par Mattea"
    assert par_regle[18]["decision"] == "parcours de Mattea" and par_regle[18]["robot_constat"] == ""
    assert par_regle[140]["decision_statut"] == "NC" and par_regle[140]["recommandation"] == "Sur Boutique A : Souligner les liens"
    lignes = list(csv.reader((dossier / "fiche.csv").open(encoding="utf-8")))
    assert lignes[0][0] == "site" and len(lignes) == 4
    assert {l[8] for l in lignes[1:]} == {"conforme", "", "non conforme"}
    assert "Boutique A" in capsys.readouterr().out
