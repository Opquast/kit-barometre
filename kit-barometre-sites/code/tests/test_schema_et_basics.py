"""Tests de generer_schema.py et synthese_esm_basics.py."""

from __future__ import annotations

import json
import sys

import pytest

import generer_schema as gs
import synthese_esm_basics as seb
from conftest import ecrire_json, lire_json


# --- generer_schema ---------------------------------------------------------

def test_e_et_chip():
    assert gs.e('<a "b">') == "&lt;a &quot;b&quot;&gt;"
    assert 'class="chip-ok"' in gs.chip(100, 10, 40, "x", "ok")


def test_card_avec_et_sans_note():
    avec = gs.card(0, 0, 100, 80, "shop", "Nom", "/c", "note", [("a", 30, "ok"), ("b", 30, "warn")])
    assert 'class="cnote"' in avec and avec.count("<rect") == 4
    assert 'class="cnote"' not in gs.card(0, 0, 100, 80, "shop", "Nom", "/c", "", [])


def test_generer_schema(racine, monkeypatch, capsys):
    r = racine(gs)
    page = r / "schema-parc.html"
    page.write_text('<html><head><style>x</style></head><body><div class="wrap">ancien</div></body></html>', encoding="utf-8")
    monkeypatch.setattr(gs, "PAGE", page)
    ecrire_json(r / "resultats/reseau-2026-11-12/resultats.json", {"services": {
        "Boutique A": {"site": [{"rule_number": 1, "status": "non-conforme"}],
                       "pages": [{"controles": [{"rule_number": 2, "status": "non-conforme"}, {"rule_number": 3, "status": "conforme"}]}]},
        "Boutique B": {"site": [], "pages": []}}})
    gs.main()
    html = page.read_text(encoding="utf-8")
    assert html.startswith("<html><head><style>x</style></head><body>")
    assert "ancien" not in html
    assert "2 non conf. réseau" in html and "0 non conf. réseau" in html and "réseau en cours" in html
    assert "2 non conforme(s) en réseau" in html and "Contrôles réseau en cours" in html
    assert "Lecture OK" in html and "Accès à ouvrir" in html
    assert "régénéré" in capsys.readouterr().out


# --- synthese_esm_basics ----------------------------------------------------

@pytest.mark.parametrize("comptes, attendu", [
    ([1, 1, 0, 0, 0], "non conforme"), ([1, 0, 0, 0, 0], "conforme"), ([0, 0, 2, 0, 0], "indéterminé"),
    ([0, 0, 0, 1, 0], "non applicable"), ([0, 0, 0, 0, 3], "non testé"), ([0, 0, 0, 0, 0], "non testé"),
])
def test_statut_site(comptes, attendu):
    assert seb.statut_site(comptes) == attendu


def test_numeros(racine):
    racine(seb)
    regles = json.loads((seb.RACINE / "referentiel/opquast-checklist-v5.json").read_text(encoding="utf-8"))
    texte = regles[0]["description"]["fr"]
    assert seb.numeros([texte.replace("'", "’")]) == [regles[0]["number"]]
    with pytest.raises(SystemExit, match="Intitulé introuvable"):
        seb.numeros(["zzzz qqqq wwww"])


def test_reseau(racine):
    r = racine(seb)
    ecrire_json(r / "resultats/reseau-2026-11-12/resultats.json", {"services": {"A": {
        "site": [{"rule_number": 1, "status": "conforme"}, {"rule_number": 1, "status": "non-conforme"}],
        "pages": [{"controles": [{"rule_number": 2, "status": "conforme"}, {"rule_number": 3, "status": "non-testé"}]}, {}]}}})
    assert seb.reseau() == {"A": {1: "non conforme", 2: "conforme", 3: "non testé"}}


def test_synthese_esm_basics(racine, monkeypatch, capsys):
    r = racine(seb)
    regles = json.loads((r / "referentiel/opquast-checklist-v5.json").read_text(encoding="utf-8"))
    par_num = {x["number"]: x["description"]["fr"] for x in regles}
    nums = [199, 217, 227, 1]
    (r / "referentiel/repartition-regles.csv").write_text("numero,methode\n199,réseau\n217,réseau\n", encoding="utf-8")
    dossier = r / "resultats/esm-basics-2026-11-12"
    ecrire_json(dossier / "agregat.json", {
        "date": "2026-11-12", "checklist": "Opquast basics", "intitules": [par_num[n] for n in nums],
        "scores": {"A": 70, "B": 80},
        "comptes": {"A": [[0, 2, 0, 0, 0], [3, 0, 0, 0, 0], [0, 0, 1, 0, 0], [0, 1, 0, 0, 0]],
                    "B": [[0, 1, 0, 0, 0], [0, 1, 0, 0, 0], [2, 0, 0, 0, 0], [0, 2, 0, 0, 0]]}})
    ecrire_json(r / "resultats/reseau-2026-11-12/resultats.json", {"services": {
        "A": {"site": [{"rule_number": 199, "status": "non-conforme"}, {"rule_number": 217, "status": "non-conforme"},
                       {"rule_number": 227, "status": "conforme"}]},
        "B": {"site": [{"rule_number": 199, "status": "conforme"}, {"rule_number": 217, "status": "non-testé"}]}}})
    monkeypatch.setattr(sys, "argv", ["seb", str(dossier)])
    seb.main()
    out = lire_json(dossier / "resultats.json")
    assert out["comparaison_reseau"] == {"accords": 1, "ecarts": [
        {"regle": 199, "site": "B", "robot": "non conforme", "script": "conforme"},
        {"regle": 217, "site": "A", "robot": "conforme", "script": "non conforme"}]}
    assert out["regles"]["1"]["methode_chez_nous"] is None
    assert out["regles"]["199"]["comptes_pages"]["A"]["non conforme"] == 2
    rapport = (dossier / "rapport.md").read_text(encoding="utf-8")
    assert "| A | 70 % | 1 | 2 | 1 | 0 | 0 |" in rapport
    assert "- **1** :" in rapport and "(méthode chez nous : ?)" in rapport
    assert "robot indéterminé / script conforme" in rapport and "script —" in rapport
    assert "1 accords, 2 écarts" in capsys.readouterr().out


def test_synthese_esm_basics_dossier_par_defaut(racine, monkeypatch, tmp_path):
    racine(seb)
    monkeypatch.chdir(tmp_path)
    ecrire_json(tmp_path / "resultats/esm-basics-2026-11-12/agregat.json",
                {"date": "d", "checklist": "c", "intitules": [], "scores": {}, "comptes": {}})
    (seb.RACINE / "referentiel/repartition-regles.csv").write_text("numero,methode\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["seb"])
    seb.main()
    assert (tmp_path / "resultats/esm-basics-2026-11-12/rapport.md").exists()
