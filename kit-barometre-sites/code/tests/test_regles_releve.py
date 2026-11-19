"""Tests de regles_releve.py (décisions tirées du relevé navigateur)."""

from __future__ import annotations

import sys

import pytest

import regles_releve as rr
from aide_parc import poser_parc
from conftest import ecrire_json, lire_json

LEGAL = """Le site est édité par la société Exemple SAS au capital de 1000 €, RCS Paris 123 456 789.
Directeur de la publication : Jean Dupont. Contact : jean.dupont@exemple.fr, 01 23 45 67 89.
Siège : 12 rue de la Paix 75002 Paris, France. Entrepôt : 3 avenue des Champs 69001 Lyon.
Nous respectons le RGAA : site conforme au RGAA.
Vous disposez d'un droit d'accès et de rectification.
Les cookies servent à la mesure d'audience. Si vous refusez les cookies, certaines fonctionnalités ne seront plus disponibles.
Livraison en 2 à 5 jours ouvrés. Frais de livraison : 4,90 €. Notre service client répond sous 48 heures.
Le débit de votre carte intervient à l'expédition de la commande. Garantie légale de conformité.
Nous livrons en France métropolitaine. Moyens de paiement : carte, PayPal. Prestataire : Shopify Payments.
Médiateur de la consommation : CM2C. Les retours sont à renvoyer à l'adresse indiquée. Frais de retour à la charge du client.
Toute réclamation peut être envoyée par e-mail au service client. Le remboursement intervient sous 14 jours.
Paiement sécurisé par 3D Secure. Service client joignable du lundi au vendredi. La carte cadeau est envoyée par e-mail.
Tout lien hypertexte vers le site est soumis à autorisation préalable. Retrouvez la dernière newsletter et les archives des newsletters.
Paiement en 3 fois sans frais avec Alma, conditions à partir de 100 €.
""" + "Texte de remplissage pour atteindre la longueur. " * 10

PAGE_ARTICLE = {"gabarit": "Article de blog", "copyright": True, "dates_texte": ["12 mars 2026"], "time_datetime": "2026-03-12",
                "maxlength": [{"signale": True}], "selects": [{"nom": "taille", "tri_alpha": True, "tri_num": False, "options": 3, "exemples": []}],
                "liens_externes": 2, "liens_externes_signales": 2, "mailto": [True], "soulignes_hors_lien": 1, "exemple_souligne": "promo",
                "regles_visited": 2, "pictos": [{"car": "★", "alternative": True}], "caps_en_dur": ["SOLDES"], "contenus_generes_texte": ["→"],
                "designation_position": ["à droite"], "listes_simulees": 1, "tableaux": [{"th": 1}], "carrousels_auto": 1, "bouton_pause": True,
                "lien_langue_textes": [{"texte": "Anglais"}], "ascii_decoratif": 1}

RICHE = {
    "fini": True, "pied_de_page": "Inscrivez-vous : un e-mail par semaine. Offrez une carte cadeau.",
    "mesures_accueil": {"nouveautes": True, "copyright": True, "langues": ["fr", "en", "x-default"], "exemple_souligne": ""},
    "mesures_produit": {"copyright": True},
    "pages": {"/blog": PAGE_ARTICLE, "/sans": {"gabarit": "Page"}},
    "panier": {"lien_vers_article": True, "ajouts_non_demandes": False, "lignes": 1, "quantite_modifiable": True, "suppression": True},
    "produit": {"caracteristiques": True, "disponibilite": True, "promo": True, "promo_dates": True, "financement": True,
                "video": [{"controles": True}]},
    "epuise": {"variantes_indisponibles": 2},
    "popup": {"presente": True, "texte": "-10 %", "bouton_fermer": True, "libelle_fermer": "Fermer", "fermer_dans_la_popup": True},
    "page_404": {"code": 404, "menu": True},
    "impression_accueil": {"nav_visible": False, "entete_visible": False},
}

PARCOURS = {"Boutique A": {"paiement": {"cases_precochees": ["Utiliser comme adresse de facturation"]}}}


@pytest.fixture(autouse=True)
def vider_pages():
    rr.PAGES_RELEVE.clear()
    yield
    rr.PAGES_RELEVE.clear()


def test_outils():
    assert rr.chercher("abc def", "zzz") is None
    assert rr.chercher("un deux trois", "deux") == "un deux trois"
    m = rr.masquer("Directeur de la publication : Jean Dupont, a@b.fr, 06 12 34 56 78")
    assert "Jean" not in m and "[adresse masquée]" in m and "[téléphone masqué]" in m and "[nom masqué]" in m
    assert rr.lecture("rien", "x", "Quoi")[0] == "NC"
    assert rr.lecture("Directeur de la publication", "publication", "Quoi")[0] == "C"


def test_decider_site_riche():
    D = rr.decider("Boutique A", RICHE, [LEGAL], PARCOURS, None)
    st = {k: v[0] for k, v in D.items()}
    for n in ("1", "2", "6", "231", "4", "101", "106", "114", "115", "16", "29", "31", "32", "38", "39", "34", "40", "42", "123",
              "65", "35", "36", "43", "44", "45", "47", "48", "49", "50", "51", "52", "53", "54", "208", "108", "109", "112", "37",
              "57", "86", "89", "74", "94", "93", "142", "144", "141", "189", "245", "126", "127", "162", "160", "161", "163",
              "225", "196", "133", "179", "177", "178"):
        assert st[n] == "C", n
    for n in ("14", "129", "151", "88", "139", "192", "184", "134"):
        assert st[n] == "NC", n
    for n in ("188", "235", "154"):
        assert st[n] == "NT", n
    assert "Jean" not in D["114"][1]
    assert "1 adresse(s) postale(s) sur 2 sans pays" in D["129"][1]


VIDE = {"fini": True, "mesures_accueil": {}, "pages": {}}


def test_decider_site_vide():
    D = rr.decider("Boutique B", VIDE, [], {}, None)
    st = {k: v[0] for k, v in D.items()}
    assert st["1"] == "NC" and st["2"] == "NC" and st["14"] == "C"
    for n in ("6", "231", "4", "37", "74", "94", "93", "142", "144", "189", "245", "126", "127", "160", "161", "162", "163", "133", "134"):
        assert st[n] == "NA", n
    for n in ("31", "32", "38", "129"):
        assert st[n] == "NT", n
    assert st["115"] == "NA" and st["151"] == "C" and st["179"] == "NC" and st["29"] == "NC" and st["192"] == "C"
    assert "39" not in D and "57" not in D and "225" not in D and "196" not in D and "154" not in D


def test_decider_variantes():
    page = {"gabarit": "Recette", "copyright": False, "dates_texte": ["12/03/26"], "meta_date": "2026", "maxlength": [{"signale": False}],
            "selects": [{"nom": "pays", "tri_alpha": False, "tri_num": False, "options": 20, "exemples": ["b", "a"]},
                        {"nom": "tri", "tri_alpha": False, "tri_num": False, "options": 3, "exemples": []}],
            "liens_externes": 2, "liens_externes_signales": 1, "mailto": [False], "pictos": [{"car": "✓", "alternative": False}],
            "tableaux": [{"th": 0}], "carrousels_auto": 2, "lien_langue_textes": [{"texte": " EN check"}, {"texte": "FR"}, {"texte": ""}]}
    s = {"fini": True, "pied_de_page": "", "mesures_accueil": {"langues": ["fr", "en"]}, "pages": {"/r": page},
         "panier": {"lignes": 2, "ajouts_non_demandes": True}, "produit": {"video": [{"controles": False}]},
         "popup": {"presente": True, "texte": "x", "bouton_fermer": False, "frequence_annoncee": True},
         "page_404": {"code": 200}, "impression_accueil": {"nav_visible": True}}
    texte = "Les cookies servent à la mesure d'audience. Une carte cadeau est en vente. Retours sous 30 jours. 4 rue Haute 75001 Paris. " + "Texte de la page légale. " * 20
    D = rr.decider("Boutique C", s, [texte], {"Boutique C": {"paiement": {"cases_precochees": []}}},
                   {"EM18": {"statut": "C"}, "EM19": {"statut": "NC"}, "EM20": {"statut": "C"}})
    st = {k: v[0] for k, v in D.items()}
    assert st["2"] == "NC" and st["6"] == "C" and st["231"] == "C" and st["4"] == "NC"
    assert st["29"] == "NC" and "conséquences" in D["29"][1]
    assert st["31"] == "NC" and st["32"] == "NC" and st["38"] == "NT"
    assert st["39"] == "NC" and st["34"] == "NT" and st["40"] == "NA" and st["42"] == "NA" and st["123"] == "NC" and st["65"] == "NT"
    assert st["37"] == "NT" and st["57"] == "NT"
    assert st["74"] == "NC" and st["94"] == "NC" and st["142"] == "NC" and st["144"] == "NC" and st["189"] == "NC" and st["245"] == "NT"
    assert st["126"] == "NC" and st["162"] == "NC" and st["160"] == "NC" and st["225"] == "NC" and st["196"] == "NC"
    assert st["134"] == "C" and st["179"] == "C"
    assert (st["174"], st["175"], st["111"]) == ("C", "NC", "C")
    tri_a_juger = dict(s, pages={"/r": dict(page, selects=[{"nom": "x", "tri_alpha": False, "tri_num": False, "options": 4, "exemples": ["a"]}])})
    assert rr.decider("Boutique C", tri_a_juger, [], {}, {"EM18": {"statut": "NT"}})["94"][0] == "NT"
    noms_libres = dict(s, pages={"/r": dict(page, lien_langue_textes=[{"texte": "Deutsch"}])})
    assert rr.decider("X", noms_libres, [], {}, None)["134"][0] == "NT"
    sans_selecteur = dict(s, pages={"/r": dict(page, lien_langue_textes=[])})
    assert rr.decider("X", sans_selecteur, [], {}, None)["134"][1] == "Sélecteur de langue non lu"
    sans_hreflang = dict(s, mesures_accueil={"langues": ["fr", "en"]})
    assert rr.decider("X", sans_hreflang, [], {}, None)["133"][0] == "C"
    assert rr.decider("X", dict(s, produit={"disponibilite": False}, epuise={"variantes_indisponibles": 1}), [], {}, None)["34"][0] == "C"


ANTI_ROBOT = "Just a moment... checking your browser"


def test_anti_robot_textes_du_releve():
    D = rr.decider("Inconnu", dict(VIDE, mesures_accueil={"copyright": False}), [ANTI_ROBOT], {}, None)
    assert D["16"][0] == "NT" and D["2"][0] == "NT"
    assert all(v[0] == "NT" for v in D.values() if v[2] == "lecture" and v[0] != "NA")


def test_anti_robot_avec_politiques():
    rr.PAGES_RELEVE["Boutique D"] = [ANTI_ROBOT]
    D = rr.decider("Boutique D", VIDE, [ANTI_ROBOT, LEGAL], {}, None)
    assert D["16"][0] == "C" and "politiques Shopify publiques" in D["16"][1]
    assert D["37"][0] == "C"


def test_textes_en_anglais():
    anglais = ("The terms of your order and the delivery of the products and your rights. " * 20)
    D = rr.decider("Boutique E", VIDE, [anglais], {}, None)
    assert D["16"][0] == "NT" and "anglais" in D["16"][1]


def test_main(racine, tmp_path, monkeypatch, capsys):
    r = poser_parc(racine, rr)
    textes = tmp_path / "textes"
    textes.mkdir()
    (textes / "Boutique_A__cgv.txt").write_text(LEGAL, encoding="utf-8")
    (textes / "Boutique_A__politique_privacy.txt").write_text(LEGAL, encoding="utf-8")
    ecrire_json(r / "resultats/releve-2026-11-12/releve.json", {
        "Boutique A": RICHE, "Boutique C": VIDE, "Boutique F": VIDE, "Boutique G": VIDE, "Boutique Z": {"fini": False}})
    ecrire_json(r / "resultats/parcours-2026-11-12/parcours.json", PARCOURS)
    ecrire_json(r / "resultats/etat-2026-11-12/etat.json", {"emails": {"Klaviyo Boutique C": {"EM18": {"statut": "C"}, "EM20": {"statut": "NC"}}}})
    ecrire_json(r / "referentiel/exclusions-sites.json", {"Boutique F": [111, 174], "Boutique G": {"regles": [57]}})
    monkeypatch.setattr(sys, "argv", ["rr", str(textes)])
    rr.main()
    out = lire_json(r / "resultats/releve-2026-11-12/decisions.json")
    assert set(out) == {"Boutique A", "Boutique C", "Boutique F", "Boutique G"}
    assert out["Boutique C"]["174"][0] == "C"
    assert out["Boutique C"]["57"][1].startswith("Non relevé sur ce site")
    assert out["Boutique G"]["111"][1].startswith("Compte e-mail pas encore connecté")
    assert "111" not in out["Boutique F"] and "57" not in out["Boutique G"]
    assert rr.PAGES_RELEVE["Boutique A"] == [LEGAL]
    assert "Boutique A" in capsys.readouterr().out


def test_dernier_absent(racine):
    racine(rr)
    assert rr.dernier("resultats/rien-*/x.json") == {}
