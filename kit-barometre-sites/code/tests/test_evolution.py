"""Tests de l'évolution entre deux passages dans exporter_csv.py (scores.csv enrichi, changements.csv, sortie console)."""

from __future__ import annotations

import csv
from datetime import date
from types import SimpleNamespace

import pytest

import consulter_barometre as cb
import exporter_csv as ex

AUJ = f"{date.today():%Y-%m-%d}"


def regle(statut, reco=""):
    return {"titre": "Titre", "theme": "Sécurité", "methode": "réseau", "statut": statut, "determinant": ["preuve"], "sources": [],
            "recommandation": reco}


def ecrire_passage(r, jour, scores, lignes):
    d = r / "resultats" / f"barometre-{jour}"
    d.mkdir(parents=True)
    ex.ecrire(d / "scores.csv", scores)
    if lignes is not None:
        ex.ecrire(d / "barometre.csv", lignes)
    return d


def lire(chemin):
    return list(csv.DictReader(chemin.open(encoding="utf-8-sig"), delimiter=";"))


@pytest.fixture
def exp(racine, monkeypatch):
    r = racine(ex, cb)
    etat = {"sites": {"Boutique A": {"1": regle("C"), "2": regle("NC", "Corriger 2"), "3": regle("C")},
                      "Boutique B": {"1": regle("NA")}, "Boutique N": {"1": regle("C")}}}
    monkeypatch.setattr(ex, "g", SimpleNamespace(ETAT={}, charger_etat=lambda: etat, charger_annexes=lambda: None, LECTURE={}, ABR={}))
    return r


def test_premier_passage(exp, capsys):
    (exp / "resultats" / "barometre-sites-exemple").mkdir()          # nom hors motif : ignoré
    (exp / "resultats" / "barometre-2020-01-01").mkdir()             # sans scores.csv : ignoré
    assert ex.main() == 0
    d = exp / "resultats" / f"barometre-{AUJ}"
    s = lire(d / "scores.csv")
    assert all(x["score_precedent"] == x["note_precedente"] == x["ecart"] == "" for x in s)
    assert (d / "changements.csv").read_text(encoding="utf-8-sig").strip() == ";".join(cb.CHAMPS_CHANGEMENTS)
    assert "premier passage, rien à comparer" in capsys.readouterr().out


def test_evolution(exp, capsys):
    ecrire_passage(exp, "2000-01-01", [{"site": "Boutique A", "score": 10, "note": "E"}], None)
    ecrire_passage(exp, "2026-01-01",
                   [{"site": "Boutique A", "score": 50, "note": "D"}, {"site": "Boutique B", "score": "", "note": "-"}],
                   [{"site": "Boutique A", "regle": 1, "intitule": "Un", "statut_retenu": "non conforme"},
                    {"site": "Boutique A", "regle": 2, "intitule": "Deux", "statut_retenu": "conforme"},
                    {"site": "Boutique A", "regle": 3, "intitule": "Trois", "statut_retenu": "non testé"},
                    {"site": "Boutique A", "regle": 4, "intitule": "Quatre", "statut_retenu": "conforme"},
                    {"site": "Boutique B", "regle": 1, "intitule": "Un", "statut_retenu": "non applicable"}])
    ecrire_passage(exp, "2999-01-01", [{"site": "Boutique A", "score": 99, "note": "A"}], None)   # futur : ignoré
    assert ex.main() == 0
    d = exp / "resultats" / f"barometre-{AUJ}"
    s = {x["site"]: x for x in lire(d / "scores.csv")}
    assert (s["Boutique A"]["score_precedent"], s["Boutique A"]["note_precedente"], s["Boutique A"]["ecart"]) == ("50", "D", "+17")
    assert (s["Boutique B"]["score_precedent"], s["Boutique B"]["ecart"]) == ("", "")
    assert s["Boutique N"]["score_precedent"] == "" and s["Boutique N"]["ecart"] == ""
    chg = lire(d / "changements.csv")
    assert [(c["regle"], c["avant"], c["apres"], c["sens"]) for c in chg] == [
        ("1", "non conforme", "conforme", "amélioration"), ("2", "conforme", "non conforme", "régression"),
        ("3", "non testé", "conforme", "autre"), ("4", "conforme", "absente", "autre")]
    assert all(c["date"] == AUJ and c["date_precedente"] == "2026-01-01" and c["site"] == "Boutique A" for c in chg)
    assert chg[3]["intitule"] == "Quatre"
    out = capsys.readouterr().out
    assert "lignes ->" in out and "Évolution (4 changements" in out
    assert "Boutique A : 50 (D) le 2026-01-01 -> 67 (C), écart +17 ; 1 amélioration, 1 régression, 2 autres changements" in out
    assert "Boutique B : - (-) le 2026-01-01 -> - (-), écart non calculable ; 0 amélioration, 0 régression, 0 autre changement" in out
    assert "Boutique N : absent du passage du 2026-01-01" in out


def test_un_seul_changement(exp, capsys):
    ecrire_passage(exp, "2026-01-01", [{"site": "Boutique A", "score": 67, "note": "C"}],
                   [{"site": "Boutique A", "regle": 1, "intitule": "Un", "statut_retenu": "conforme"},
                    {"site": "Boutique A", "regle": 2, "intitule": "Deux", "statut_retenu": "non conforme"}])
    assert ex.main() == 0
    out = capsys.readouterr().out
    assert "Évolution (1 changement ->" in out and "écart 0 ; 0 amélioration, 0 régression, 1 autre changement" in out


def test_aides():
    assert cb.ecart(5, 7) == "-2" and cb.ecart("3", "3") == "0" and cb.ecart(None, 3) == "" and cb.ecart("", "x") == ""
    assert cb.sens("non applicable", "conforme") == "autre"
    assert cb.changements([{"site": "X", "regle": "a", "statut_retenu": "conforme"}],
                          [{"site": "X", "regle": "1", "intitule": "Un", "statut_retenu": "conforme"},
                           {"site": "Y", "regle": "1", "statut_retenu": "conforme"}]) == [
        {"site": "X", "regle": "1", "intitule": "Un", "avant": "absente", "apres": "conforme", "sens": "autre"},
        {"site": "X", "regle": "a", "intitule": "", "avant": "conforme", "apres": "absente", "sens": "autre"}]


def test_passages_sans_resultats(tmp_path):
    assert cb.passages(tmp_path) == [] and cb.lire_csv(tmp_path / "x.csv") == []
