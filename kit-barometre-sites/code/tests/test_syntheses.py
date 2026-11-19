"""Tests de verifier_page_a4.py, fusion_scripts.py et synthese_axe.py."""

from __future__ import annotations

import json
import sys
from datetime import date
from types import SimpleNamespace

import pytest

import fusion_scripts as fs
import synthese_axe as sa
import verifier_page_a4 as a4
from aide_parc import poser_parc
from conftest import ecrire_json, lire_json


# --- verifier_page_a4 -------------------------------------------------------

def test_inline():
    assert a4.inline("**gras** `code` [lien](https://x) <b>") == "<strong>gras</strong> <code>code</code> lien &lt;b&gt;"


def test_md_vers_html():
    md = "# Titre\n\nUn paragraphe.\n- a\n- b\n1. un\n2. deux\n| A | B |\n|---|---|\n| 1 | 2 |\n## Fin"
    h = a4.md_vers_html(md)
    for morceau in ("<h1>Titre</h1>", "<p>Un paragraphe.</p>", "<ul>", "<li>b</li>", "<ol>", "<li>deux</li>",
                    "<th>A</th>", "<td>2</td>", "<h2>Fin</h2>"):
        assert morceau in h


@pytest.mark.parametrize("pages, code, copie", [(1, 0, False), (2, 1, True)])
def test_main_a4(tmp_path, monkeypatch, capsys, pages, code, copie):
    source = tmp_path / "note.md"
    source.write_text("# Note", encoding="utf-8")
    argv = ["a4", str(source)] + ([str(tmp_path / "copie.pdf")] if copie else [])
    monkeypatch.setattr(sys, "argv", argv)

    def faux_run(cmd, **kw):
        if cmd[0] == a4.CHROME:
            next(a for a in cmd if a.startswith("--print-to-pdf=")).split("=", 1)[1]
            open(next(a for a in cmd if a.startswith("--print-to-pdf=")).split("=", 1)[1], "wb").write(b"%PDF")
            return SimpleNamespace(stdout="")
        return SimpleNamespace(stdout=f"Title: x\nPages:          {pages}\n")

    monkeypatch.setattr(a4.subprocess, "run", faux_run)
    assert a4.main() == code
    assert f"{pages} page(s) A4" in capsys.readouterr().out
    assert (tmp_path / "copie.pdf").exists() == copie


def test_main_a4_fichier_par_defaut(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note_cadrage.md").write_text("texte", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["a4"])
    monkeypatch.setattr(a4.subprocess, "run", lambda cmd, **kw: SimpleNamespace(stdout="Pages: 1"))
    assert a4.main() == 0


# --- fusion_scripts ---------------------------------------------------------

def test_charger(racine, monkeypatch):
    r = racine(fs)
    ecrire_json(r / "resultats/reseau-2026-11-05/resultats.json", {"services": {"Boutique A": {"v": 1}, "Boutique B": {"v": 1}}})
    ecrire_json(r / "resultats/reseau-2026-11-12/resultats.json", {"services": {"Boutique A": {"v": 2}}})
    ecrire_json(r / "resultats/reseau-2026-11-12-essai/resultats.json", {"services": {"Boutique A": {"v": 3}}})
    assert fs.charger("reseau") == {"Boutique A": {"v": 2}, "Boutique B": {"v": 1}}
    monkeypatch.setattr(fs, "SAUF", {"reseau"})
    assert fs.charger("reseau") == {}


def test_fusion_main(racine, capsys):
    r = poser_parc(racine, fs)
    (r / "scripts" / "ecrans_en_ligne.csv").write_text(
        "service,gabarit,url\nBoutique A,Accueil,https://a.fr/\nBoutique A,Panier,https://a.fr/cart\n", encoding="utf-8")
    (r / "referentiel" / "repartition-regles.csv").write_text(
        "numero,methode\n1,réseau\n2,page\n3,page\n4,IA\n", encoding="utf-8")
    ecrire_json(r / "resultats/reseau-2026-11-12/resultats.json", {"services": {"Boutique A": {
        "site": [{"rule_number": 1, "status": "conforme", "comment": "écrire à mailto:x@y.fr"}],
        "pages": [{"url": "https://a.fr/cart", "controles": [{"rule_number": 2, "status": "non-applicable"}]}]}}})
    ecrire_json(r / "resultats/page-2026-11-12/resultats.json", {"services": {"Boutique A": {"pages": [
        {"url": "https://a.fr/", "controles": [
            {"rule_number": 1, "status": "non-conforme", "comment": "ko"},
            {"rule_number": 3, "status": "non-testé", "comment": "?"},
            {"rule_number": 4, "status": "conforme", "comment": "hors 82"}]},
        {"url": "https://a.fr/cart", "controles": [{"rule_number": 3, "status": "conforme", "comment": "ok"}]},
        {"url": "https://ailleurs.fr/"}]}}})
    fs.main()
    pages = lire_json(r / "resultats" / f"esm-scripts-{date.today():%Y-%m-%d}" / "WEB-BOUTIQUEA.json")
    assert pages[0]["titre"] == "Accueil"
    assert pages[0]["resultats"] == {"1": ["NC", "[controles_reseau.py] écrire à mailto:[masqué] | [controles_page.js] ko"]}
    assert pages[1]["titre"] == "Panier"
    assert pages[1]["resultats"] == {"2": ["NA", "[controles_reseau.py] "], "3": ["C", "[controles_page.js] ok"]}
    assert lire_json(r / "resultats" / f"esm-scripts-{date.today():%Y-%m-%d}" / "WEB-BOUTIQUEB.json") == []
    assert "Boutique A : 3 résultats (1 non conformes) sur 2 pages" in capsys.readouterr().out


# --- synthese_axe -----------------------------------------------------------

def test_critere():
    assert sa.critere("wcag143") == "1.4.3"
    assert sa.critere("wcag2411") == "2.4.11"


def test_synthese_axe(tmp_path, monkeypatch, capsys):
    dossier = tmp_path / "axe-2026-11-12"
    dossier.mkdir()
    (dossier / "brut.tsv").write_text(
        "service\tgabarit\tchemin\tregles_respectees\ta_verifier\tviolations\n"
        "Boutique A\tAccueil\t/\t40\t3\timage-alt:critical:wcag111:2;regle-inconnue:bizarre:wcag412:1\n"
        "Boutique A\tProduit\t/p\t41\t2\timage-alt:critical:wcag111:1;color-contrast:serious:wcag143:5\n"
        "Boutique A\tCompte\t/account\tNT\t\t\n"
        "Boutique B\tAccueil\t/\t45\t0\t\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["sa", str(dossier)])
    sa.main()
    out = lire_json(dossier / "resultats.json")
    a = out["sites"]["Boutique A"]
    assert out["date"] == "2026-11-12"
    assert (a["pages_testees"], a["pages_non_testees"], a["regles_en_violation"], a["regles_critiques"], a["elements_en_defaut"]) == (2, 1, 3, 1, 9)
    assert a["regles"]["image-alt"] == {"gravite": "critical", "criteres": ["1.1.1"], "pages": 2, "elements": 3}
    rapport = (dossier / "rapport.md").read_text(encoding="utf-8")
    assert "| Image sans texte alternatif | `image-alt` | 1.1.1 | critique | 2 | 3 |" in rapport
    assert "| regle-inconnue | `regle-inconnue` | 4.1.2 | bizarre | 1 | 1 |" in rapport
    assert "- Non testé : Compte (/account)." in rapport
    assert "2 sites" in capsys.readouterr().out


def test_synthese_axe_dossier_par_defaut(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "resultats" / "axe-2026-11-12"
    d.mkdir(parents=True)
    (d / "brut.tsv").write_text("service\tgabarit\tchemin\tregles_respectees\ta_verifier\tviolations\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["sa"])
    sa.main()
    assert json.loads((d / "resultats.json").read_text(encoding="utf-8"))["sites"] == {}
