"""Tests de verifier_publication.py, regles_une_source.py et des replis sans eServices Manager."""

from __future__ import annotations

from datetime import date

import etat_barometre as eb
import fiche_contre_examen as fce
import regles_une_source as rus
import verifier_publication as vp
from aide_parc import PARC_ORIGINE, poser_parc
from conftest import ecrire_json, lire_json


# --- verifier_publication ---------------------------------------------------

def test_dossiers_du_dernier_passage(tmp_path):
    assert vp.dossiers_du_dernier_passage(tmp_path / "absent") == []
    for nom in ("reseau-2026-11-18", "axe-2026-11-19", "page-2026-11-19", "journal-sans-date", "esm-basics-2026-11-12"):
        (tmp_path / nom).mkdir()
    (tmp_path / "rapport-2026-11-20.log").write_text("", encoding="utf-8")
    assert [d.name for d in vp.dossiers_du_dernier_passage(tmp_path)] == ["axe-2026-11-19", "page-2026-11-19"]


def test_trouver():
    assert vp.trouver("contact@boutique.fr et logo@2x.png, jean@exemple.fr, @media x") == ["contact@boutique.fr"]
    assert vp.trouver("Appelez le 01 23 45 67 89") == ["01 23 45 67 89"]
    assert vp.trouver("rien") == []


def test_rien_a_verifier(racine, capsys):
    racine(vp)
    assert vp.main() == vp.CODE_RIEN_A_VERIFIER
    assert "rien n'a été vérifié" in capsys.readouterr().err


def test_publication_propre_puis_sale(racine, capsys):
    r = racine(vp)
    ecrire_json(r / "resultats/reseau-2026-11-18/resultats.json", {"x": "ancien@vrai.fr"})
    ecrire_json(r / "resultats/axe-2026-11-19/resultats.json", {"x": "propre"})
    (r / "resultats/axe-2026-11-19/image.png").write_bytes(b"\x89PNG 06 12 34 56 78")
    (r / "suivi-barometre.html").write_text("<p>@media écran</p>", encoding="utf-8")
    assert vp.main() == 0
    assert "2 fichier(s) vérifié(s), 0" in capsys.readouterr().out
    (r / "resultats/axe-2026-11-19/brut.tsv").write_text("a\nécrire à moi@vrai.fr\n", encoding="utf-8")
    assert vp.main() == vp.CODE_TROUVE
    assert "resultats/axe-2026-11-19/brut.tsv:2 : « moi@vrai.fr »" in capsys.readouterr().err


def test_page_seule(racine):
    r = racine(vp)
    (r / "suivi-barometre.html").write_text("tel 0612345678", encoding="utf-8")
    assert vp.main() == vp.CODE_TROUVE


# --- regles_une_source ------------------------------------------------------

def test_regles_une_source(racine, tmp_path, capsys):
    r = racine(rus)
    hors = tmp_path / "hors"
    assert rus.main([]) == 2
    assert rus.main([str(hors)]) == 1
    assert "lancer d'abord l'étape synthese" in capsys.readouterr().err
    ecrire_json(r / "resultats/lecture-critique-2026-11-19/lecture.json", {
        "Boutique A": {"sources_par_regle": {"1": ["a", "b"], "2": ["a"], "3": []}},
        "Boutique B": {},
        "_emails": {"x": {}}})
    assert rus.main([str(hors)]) == 0
    assert lire_json(hors / "regles_une_source.json") == {"Boutique A": ["2", "3"], "Boutique B": []}
    assert "Boutique A 2 règle(s)" in capsys.readouterr().out


# --- replis sans eServices Manager ------------------------------------------

def test_etat_sans_esm(racine, monkeypatch, capsys):
    r = poser_parc(racine, eb, donnees={"sites": [PARC_ORIGINE["sites"][0]]})
    eb.main()
    sortie = capsys.readouterr().out
    assert "Aucun export Opquast basics" in sortie and "Aucune fusion des scripts" in sortie
    etat = lire_json(r / "resultats" / f"etat-{date.today():%Y-%m-%d}" / "etat.json")
    assert etat["sites"] == {"Boutique A": {}}


def test_etat_fichiers_partiels(racine, monkeypatch):
    r = poser_parc(racine, eb, donnees={"sites": [PARC_ORIGINE["sites"][0]]})
    (r / "resultats/esm-scripts-2026-11-12").mkdir(parents=True)
    (r / "resultats/esm-basics-2026-11-12").mkdir(parents=True)
    eb.main()
    assert lire_json(r / "resultats" / f"etat-{date.today():%Y-%m-%d}" / "etat.json")["sites"] == {"Boutique A": {}}


def test_fiche_sans_etat(racine, capsys):
    racine(fce)
    assert fce.main() is None
    assert "Aucun état consolidé" in capsys.readouterr().out


def test_fiche_sans_esm_ni_constats(racine):
    r = racine(fce)
    ecrire_json(r / "resultats/etat-2026-11-12/etat.json", {"sites": {"Boutique A": {"216": {"robot": None, "titre": "Fenêtre"}}}})
    (r / "referentiel/repartition-regles.csv").write_text("numero,methode\n216,manuel\n", encoding="utf-8")
    fce.main()
    fiche = lire_json(r / "resultats" / f"contre-examen-{date.today():%Y-%m-%d}" / "fiche.json")
    assert fiche["Boutique A"][0]["regle"] == 216 and fiche["Boutique A"][0]["robot_constat"] == ""
