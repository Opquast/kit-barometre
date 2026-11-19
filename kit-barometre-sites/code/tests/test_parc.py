"""Tests de parc.py (lecture du parc) et configurer_parc.py (création, complément et vérification de parc.json)."""

from __future__ import annotations

import pytest

import configurer_parc as cp
import parc
from aide_parc import PARC_ORIGINE, poser_parc
from conftest import ecrire_json, lire_json

ECRANS = ("service,gabarit,url\n"
          "Boutique A,Accueil,https://a.fr/\nBoutique A,Panier,https://a.fr/cart\n"
          "Boutique D,Collection,https://d.fr/fr/collections/x\nBoutique D,Accueil FR,https://d.fr/fr\n"
          "Été,Produit,https://e.fr/en-gb/products/p\n")


# --- parc.py -----------------------------------------------------------------

def test_lecture_du_parc_d_origine(racine):
    r = poser_parc(racine)
    assert parc.fichier() == r / "referentiel" / "parc.json"
    assert parc.fichier(r) == parc.fichier() and parc.fichier(r / "autre.json") == r / "autre.json"
    assert parc.noms()[0] == "Boutique A" and len(parc.sites()) == 6
    assert parc.responsable() == "Mattea" and parc.auditeur_esm() == "MLU"
    assert parc.par_nom()["Boutique D"]["prefixe_langue"] == "/fr"
    assert parc.codes_esm()["Boutique C"] == "WEB-BOUTIQUEC"
    assert parc.shopify() == parc.noms() and parc.hors_site() == {"Boutique C", "Boutique D", "Boutique E"}
    assert parc.comptes_email() == {"Boutique C": "Klaviyo Boutique C", "Boutique F": "Klaviyo Boutique F"}


def test_parc_absent_ou_incomplet(racine, tmp_path):
    poser_parc(racine, donnees={"responsable": "", "sites": [{"nom": "X", "code_esm": "WEB-X", "plateforme": "wordpress"}, {"nom": "Y"}]})
    assert parc.responsable() == parc.RESPONSABLE_DEFAUT and parc.auditeur_esm() == ""
    assert parc.shopify() == ["Y"] and parc.hors_site() == set() and parc.comptes_email() == {}
    vide = tmp_path / "rien"
    assert parc.charger(vide) == {"responsable": parc.RESPONSABLE_DEFAUT, "sites": []} and parc.sites(vide) == []


# --- configurer_parc.py : fonctions ------------------------------------------

@pytest.mark.parametrize("nom, code, prefixe", [
    ("Boutique A", "WEB-BOUTIQUEA", "BA"), ("Ma boutique", "WEB-MABOUTIQUE", "MB"), ("Été", "WEB-ETE", "ETE"),
    ("Chaussures", "WEB-CHAUSSURES", "CHAU"), ("!!!", "WEB-SITE", "SITE"),
])
def test_codes_par_defaut(nom, code, prefixe):
    assert cp.code_esm(nom) == code and cp.prefixe_pages(nom) == prefixe


@pytest.mark.parametrize("url, attendu", [
    ("https://d.fr/fr", "/fr"), ("https://d.fr/FR/", "/fr"), ("https://e.fr/en-gb/products/p", "/en-gb"),
    ("https://a.fr/", ""), ("https://a.fr/collections/x", ""), ("", ""),
])
def test_prefixe_langue(url, attendu):
    assert cp.prefixe_langue(url) == attendu


def test_defauts():
    ecrans = [{"service": "D", "gabarit": "Collection", "url": "https://d.fr/collections/x"},
              {"service": "D", "gabarit": "Accueil FR", "url": "https://d.fr/fr"}]
    assert cp.defauts("D", ecrans) == {"nom": "D", "code_esm": "WEB-D", "prefixe_pages": "D", "plateforme": "shopify",
                                       "compte_client_hors_site": True, "prefixe_langue": "/fr", "compte_email": ""}
    assert cp.defauts("D", ecrans[:1])["prefixe_langue"] == "" and cp.defauts("Z", [])["prefixe_langue"] == ""


def test_completer_garde_l_existant():
    ecrans = [{"service": "A", "gabarit": "Accueil", "url": "https://a.fr/"}, {"service": "B", "gabarit": "Accueil", "url": "https://b.fr/"},
              {"service": "C", "gabarit": "Accueil", "url": "https://c.fr/"}]
    donnees = {"_aide": "à moi", "responsable": "Alex", "note": 1, "sites": [
        {"nom": "B", "code_esm": "WEB-PERSO", "plateforme": "wordpress"},
        {"nom": "A", **{k: v for k, v in cp.defauts("A", ecrans).items() if k != "nom"}},
        {"nom": "C", "plateforme": "shopify", "compte_client_hors_site": False},
        {"nom": "Vieux", "code_esm": "WEB-V"}]}
    out, ajouts = cp.completer(donnees, ecrans + [{"service": "N", "gabarit": "Accueil", "url": "https://n.fr/"}], auditeur="AB")
    assert [s["nom"] for s in out["sites"]] == ["A", "B", "C", "N", "Vieux"]
    b = out["sites"][1]
    assert b["code_esm"] == "WEB-PERSO" and b["plateforme"] == "wordpress" and b["compte_client_hors_site"] is False and b["prefixe_pages"] == "B"
    assert out["sites"][2]["compte_client_hors_site"] is False
    assert (out["_aide"], out["responsable"], out["auditeur_esm"], out["note"]) == ("à moi", "Alex", "AB", 1)
    assert ajouts == ["B : champs complétés (prefixe_pages, compte_client_hors_site, prefixe_langue, compte_email)",
                      "C : champs complétés (code_esm, prefixe_pages, prefixe_langue, compte_email)",
                      "site ajouté : N (WEB-N, préfixe N)"]
    neuf, _ = cp.completer({}, ecrans[:1], responsable="Sam")
    assert neuf["_aide"] == cp.AIDE and neuf["responsable"] == "Sam" and neuf["auditeur_esm"] == ""


def test_verifier():
    ecrans = [{"service": "A"}, {"service": "B"}, {"service": "A"}]
    complet = lambda nom, code, pre: {**cp.defauts(nom, []), "code_esm": code, "prefixe_pages": pre}
    assert cp.verifier({"sites": [complet("A", "WEB-A", "A"), complet("B", "WEB-B", "B")]}, ecrans) == []
    pb = cp.verifier({"sites": [complet("A", "WEB-A", "P"), complet("A", "WEB-A", "P"), complet("Z", "WEB-Z", "Z"), {"nom": "Q"}]}, ecrans)
    assert "site du CSV absent du parc : B" in pb and "site du parc absent du CSV : Z" in pb
    assert "nom en double : A (2 sites)" in pb and "code eServices Manager en double : WEB-A (2 sites)" in pb
    assert "préfixe de pages en double : P (2 sites)" in pb and "Q : champ manquant code_esm" in pb


# --- configurer_parc.py : main -----------------------------------------------

def test_main_cree_le_parc(racine, capsys):
    r = racine(cp, parc)
    (r / "referentiel" / "parc.json").unlink()
    (r / "scripts" / "ecrans_en_ligne.csv").write_text(ECRANS, encoding="utf-8")
    assert cp.main(["--responsable", "Alex", "--auditeur-esm", "AL"]) == 0
    d = lire_json(r / "referentiel" / "parc.json")
    assert [s["nom"] for s in d["sites"]] == ["Boutique A", "Boutique D", "Été"]
    assert d["sites"][1]["prefixe_langue"] == "/fr" and d["sites"][2]["prefixe_langue"] == "/en-gb"
    assert (d["responsable"], d["auditeur_esm"]) == ("Alex", "AL")
    out = capsys.readouterr().out
    assert "3 site(s), responsable : Alex" in out and "site ajouté : Été (WEB-ETE, préfixe ETE)" in out and "Parc cohérent" in out
    # relancé sans option : rien ne change
    assert cp.main([]) == 0 and lire_json(r / "referentiel" / "parc.json") == d


def test_main_verifier_seulement(racine, capsys):
    r = poser_parc(racine, cp)
    (r / "scripts" / "ecrans_en_ligne.csv").write_text(ECRANS, encoding="utf-8")
    avant = (r / "referentiel" / "parc.json").read_text(encoding="utf-8")
    assert cp.main(["--verifier"]) == 1
    assert (r / "referentiel" / "parc.json").read_text(encoding="utf-8") == avant
    out = capsys.readouterr().out
    assert "INCOHÉRENCE site du CSV absent du parc : Été" in out and "INCOHÉRENCE site du parc absent du CSV : Boutique B" in out


def test_main_incoherence_apres_complement(racine, tmp_path, capsys):
    """Le complément ajoute les sites du CSV mais garde ceux du parc absents du CSV : code 1 ; chemins passés en option."""
    f_parc, f_ecrans = tmp_path / "p" / "parc.json", tmp_path / "e.csv"
    ecrire_json(f_parc, {"sites": [dict(PARC_ORIGINE["sites"][1])]})
    f_ecrans.write_text(ECRANS, encoding="utf-8")
    racine(cp)
    assert cp.main(["--parc", str(f_parc), "--ecrans", str(f_ecrans)]) == 1
    assert [s["nom"] for s in lire_json(f_parc)["sites"]] == ["Boutique A", "Boutique D", "Été", "Boutique B"]
    assert "INCOHÉRENCE site du parc absent du CSV : Boutique B" in capsys.readouterr().out


def test_main_fichiers_absents_ou_illisibles(racine, tmp_path, capsys):
    racine(cp)
    assert cp.main(["--ecrans", str(tmp_path / "absent.csv")]) == 2
    f = tmp_path / "parc.json"
    f.write_text("{pas du json", encoding="utf-8")
    assert cp.main(["--parc", str(f), "--verifier"]) == 2
    out = capsys.readouterr().out
    assert "Fichier des écrans absent" in out and "illisible" in out
