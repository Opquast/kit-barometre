"""Tests de consulter_barometre.py (mode consultation, sans relancer de passage)."""

from __future__ import annotations

import pytest

import consulter_barometre as cb
import exporter_csv as ex


def passage(r, jour, scores, lignes):
    d = r / "resultats" / f"barometre-{jour}"
    d.mkdir(parents=True)
    ex.ecrire(d / "scores.csv", scores)
    ex.ecrire(d / "barometre.csv", lignes)


def ligne(site, n, statut, reco=""):
    return {"site": site, "regle": n, "intitule": f"Règle {n}", "statut_retenu": statut, "recommandation": reco}


@pytest.fixture
def deux(racine):
    r = racine(cb)
    passage(r, "2026-01-01", [{"site": "Boutique A", "score": 50, "note": "D"}, {"site": "Boutique B", "score": "", "note": "-"}],
            [ligne("Boutique A", 1, "non conforme", "Corriger 1"), ligne("Boutique A", 2, "conforme"), ligne("Boutique A", 4, "non testé"), ligne("Boutique B", 1, "non applicable")])
    passage(r, "2026-02-01", [{"site": "Boutique A", "score": 67, "note": "C"}, {"site": "Boutique C", "score": 100, "note": "A"}],
            [ligne("Boutique A", 1, "conforme"), ligne("Boutique A", 2, "non conforme", "Corriger 2"), ligne("Boutique A", 3, "non conforme"),
             ligne("Boutique A", 4, "non testé"), ligne("Boutique C", 1, "conforme")])
    return r


def test_aucun_passage(racine, capsys):
    racine(cb)
    assert cb.main([]) == 1
    assert "Aucun passage" in capsys.readouterr().err


def test_tous_les_sites(deux, capsys):
    assert cb.main([]) == 0
    out = capsys.readouterr().out
    assert "2 passages, le dernier le 2026-02-01" in out
    assert "Boutique A - dernier passage le 2026-02-01" in out and "Score : 67/100, note C" in out
    assert "Évolution depuis le 2026-01-01 : 50 (D) -> 67 (C), écart +17 ; 1 amélioration, 1 régression, 1 autre changement" in out
    assert "Règles non conformes : 2" in out and "- 2 Règle 2 : Corriger 2" in out and "- 3 Règle 3\n" in out
    assert "Boutique B - dernier passage le 2026-01-01" in out and "Score : -/100, note -" in out
    assert "Boutique C - dernier passage le 2026-02-01" in out and "premier passage pour ce site" in out


def test_un_site_et_une_regle(deux, capsys):
    assert cb.main(["--site", "Boutique A", "--regle", "2"]) == 0
    out = capsys.readouterr().out
    assert "Boutique B" not in out and "Règle 2 - Règle 2" in out and "Statut retenu : non conforme" in out
    assert "Statut au passage précédent : conforme (régression)" in out and "Recommandation : Corriger 2" in out
    assert cb.main(["--regle", "1"]) == 0
    out = capsys.readouterr().out
    assert "Statut au passage précédent : non conforme (amélioration)" in out
    assert out.count("Statut retenu : conforme") == 2   # Boutique A et Boutique C (sans passage précédent)
    assert "Recommandation" not in out
    assert cb.main(["--site", "Boutique A", "--regle", "4"]) == 0
    assert "Statut au passage précédent : non testé (inchangé)" in capsys.readouterr().out


def test_inconnus(deux, capsys):
    assert cb.main(["--site", "Inconnue"]) == 2
    assert "Site inconnu : Inconnue. Sites mesurés : Boutique A, Boutique B, Boutique C" in capsys.readouterr().err
    assert cb.main(["--regle", "99"]) == 2
    assert "Règle 99 : absente de ce passage" in capsys.readouterr().out


def test_un_seul_passage(racine, capsys):
    r = racine(cb)
    passage(r, "2026-01-01", [{"site": "Boutique A", "score": 50, "note": "D"}], [ligne("Boutique A", 1, "non conforme")])
    assert cb.main([]) == 0
    assert "1 passage, le dernier" in capsys.readouterr().out
