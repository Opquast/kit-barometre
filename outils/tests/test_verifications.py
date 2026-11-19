"""Tests des scripts de contrôle de outils/verifications."""

from __future__ import annotations

import openpyxl
import pytest

import donnees_personnelles as dp
import partage
import structure_skill as ss


# --- donnees_personnelles ---------------------------------------------------

@pytest.mark.parametrize("valeur, attendu", [
    ("contact@boutique.fr", 1),
    ("jean@example.com", 0),
    ("a@shop.exemple.fr", 0),
    ("06 12 34 56 78", 1),
    ("+33 6 12 34 56 78", 1),
    ("score 66 ; 2026-11-19", 0),
    ("3.0612345678", 0),
    ("", 0),
])
def test_controler_cellule(valeur, attendu):
    assert len(dp.controler_cellule(valeur)) == attendu


def test_controler_lignes_vide():
    assert dp.controler_lignes([]) == []


def test_controler_lignes_colonne_nominative():
    lignes = [["\ufeffNom", "score"], ["Dupont", "66"], ["", "70"], [None, "1"]]
    assert dp.controler_lignes(lignes) == ["ligne 2 : colonne nominative « nom » remplie"]


def test_controler_lignes_email_dans_entete_et_corps():
    lignes = [["site", "contact"], ["A", "x@vrai.fr"]]
    assert dp.controler_lignes(lignes) == ["ligne 2 : adresse e-mail « x@vrai.fr »"]


def test_fichier_csv_point_virgule(tmp_path):
    f = tmp_path / "a.csv"
    f.write_text("\ufeffsite;email\nA;moi@vrai.fr\n", encoding="utf-8")
    problemes = dp.controler_fichier(f)
    assert len(problemes) == 2
    assert all(str(f) in p for p in problemes)


def test_fichier_csv_non_detectable(tmp_path):
    f = tmp_path / "a.csv"
    f.write_text("x", encoding="utf-8")
    assert dp.controler_fichier(f) == []


def test_fichier_excel(tmp_path):
    f = tmp_path / "a.xlsx"
    classeur = openpyxl.Workbook()
    feuille = classeur.active
    feuille.title = "Scores"
    feuille.append(["site", "telephone"])
    feuille.append(["A", "01 23 45 67 89"])
    classeur.save(f)
    problemes = dp.controler_fichier(f)
    assert len(problemes) == 2
    assert all("[Scores]" in p for p in problemes)


def test_fichier_autre_extension(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("moi@vrai.fr", encoding="utf-8")
    assert dp.controler_fichier(f) == []


def test_main_dp(tmp_path, capsys):
    propre = tmp_path / "ok.csv"
    propre.write_text("site;score\nA;1\n", encoding="utf-8")
    sale = tmp_path / "ko.csv"
    sale.write_text("site;mail\nA;x@vrai.fr\n", encoding="utf-8")
    assert dp.main([str(propre)]) == 0
    assert dp.main([str(propre), str(sale)]) == 1
    assert "Donnée personnelle" in capsys.readouterr().err


# --- partage ----------------------------------------------------------------

@pytest.mark.parametrize("texte, attendu", [
    ("cd /Users/mickaelh/Documents", 1),
    ("voir /home/jean/projet", 1),
    (r"C:\Users\jean\Desktop", 1),
    ("/Users/<nom>/projet et /home/$USER", 0),
    ("https://claude.ai/artifact/12y1tK8TKX8uMtbi92d1Q8", 1),
    ("https://claude.ai/code/artifact/0b8f1c2e-aaaa", 1),
    ("chemin relatif scripts/barometre.py", 0),
])
def test_controler_texte(texte, attendu):
    assert len(partage.controler_texte(texte)) == attendu


def test_partage_fichier_binaire(tmp_path):
    f = tmp_path / "a.bin"
    f.write_bytes(b"\0/Users/jean/")
    assert partage.controler_fichier(f) == []


def test_partage_main(tmp_path, capsys):
    ok = tmp_path / "ok.md"
    ok.write_text("rien", encoding="utf-8")
    ko = tmp_path / "ko.md"
    ko.write_text("ligne\n/Users/jean/x", encoding="utf-8")
    assert partage.main([str(ok)]) == 0
    assert partage.main([str(ko)]) == 1
    assert "ligne 2" in capsys.readouterr().err


# --- structure_skill --------------------------------------------------------

def faire_skill(base, nom="ma-skill", frontmatter=None, corps=""):
    dossier = base / "projet" / ".claude" / "skills" / nom
    dossier.mkdir(parents=True)
    if frontmatter is None:
        frontmatter = f"---\nname: {nom}\ndescription: Fait une chose.\n---\n"
    (dossier / "SKILL.md").write_text(frontmatter + corps, encoding="utf-8")
    return dossier


@pytest.mark.parametrize("frontmatter, message", [
    ("# Titre\n", "frontmatter absent"),
    ("---\nname: x\n", "non refermé"),
    ("---\nname: [x\n---\n", "YAML invalide"),
    ("---\n- a\n---\n", "vide ou mal formé"),
    ("---\ndescription: d\n---\n", "« name » manquant"),
    ("---\nname: autre\ndescription: d\n---\n", "différent du dossier"),
    ("---\nname: ma-skill\ndescription: ' '\n---\n", "« description » manquant"),
    ("---\nname: ma-skill\ndescription: " + "x" * 1025 + "\n---\n", "trop longue"),
])
def test_frontmatter_invalide(tmp_path, frontmatter, message):
    dossier = faire_skill(tmp_path, frontmatter=frontmatter)
    problemes = ss.controler_frontmatter(dossier / "SKILL.md")
    assert len(problemes) == 1 and message in problemes[0]


def test_frontmatter_valide(tmp_path):
    assert ss.controler_frontmatter(faire_skill(tmp_path) / "SKILL.md") == []


def test_references_filtrees():
    texte = ("`scripts/a.py` `referentiel/b.json` `resultats/<date>/x.json` `scripts/*.py` "
             "`note.md` [lien](https://x.fr/scripts/a) [doc](./references/c.md) [ancre](#titre)")
    assert ss.references(texte) == {"scripts/a.py", "referentiel/b.json", "./references/c.md"}


def test_controler_references(tmp_path):
    dossier = faire_skill(tmp_path, corps="`scripts/present.py` `scripts/absent.py` [r](./references/r.md)\n")
    (dossier / "references").mkdir()
    (dossier / "references" / "r.md").write_text("`assets/rien.md`", encoding="utf-8")
    racine = dossier.parents[2]
    (racine / "scripts").mkdir()
    (racine / "scripts" / "present.py").write_text("", encoding="utf-8")
    problemes = ss.controler_references(dossier)
    assert problemes == [
        "SKILL.md cite « scripts/absent.py », introuvable",
        "references/r.md cite « assets/rien.md », introuvable",
    ]


def test_racine_projet_hors_claude(tmp_path):
    assert ss.racine_projet(tmp_path / "x") == tmp_path / "x"


def test_dossier_de_skill(tmp_path):
    dossier = faire_skill(tmp_path)
    (dossier / "references").mkdir()
    assert ss.dossier_de_skill(dossier / "references" / "x.md") == dossier
    assert ss.dossier_de_skill(tmp_path) is None


def test_main_avec_arguments(tmp_path, capsys):
    bonne = faire_skill(tmp_path)
    assert ss.main([str(bonne / "SKILL.md"), str(tmp_path)]) == 0
    mauvaise = faire_skill(tmp_path / "b", nom="b", corps="`scripts/absent.py`")
    assert ss.main([str(mauvaise / "SKILL.md")]) == 1
    assert "absent.py" in capsys.readouterr().err


def test_main_sans_argument(tmp_path, monkeypatch):
    faire_skill(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert ss.main([]) == 0
