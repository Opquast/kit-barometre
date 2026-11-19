"""Tests de valider_lectures.py et preparer_lectures.py (lectures IA indépendantes)."""

from __future__ import annotations

import json
from datetime import date

import pytest

import preparer_lectures as pl
import valider_lectures as vl
from conftest import ecrire_json, lire_json

CFG = vl.charger_lectures()["lectures"]
SITES = {"Boutique A", "Boutique B"}


def parc_test(r, noms=("Boutique A", "Boutique B")):
    ecrire_json(r / "referentiel/parc.json", {"responsable": "Camille", "sites": [{"nom": n} for n in noms]})


def test_referentiel_coherent():
    conf = vl.charger_lectures()
    assert set(conf["lectures"]) == {"1", "2", "3"} and conf["bilan_max_lignes"] == 15
    for cfg in conf["lectures"].values():
        assert "{n}" in cfg["sortie"] and cfg["preuve"] in ("citation", "capture", "dom_ou_capture")
        if isinstance(cfg["regles"], list):
            assert cfg["regles"] == sorted(set(cfg["regles"])) and all(1 <= k <= 245 for k in cfg["regles"])
    assert vl.prefixe("Boutique  D'été") == "Boutique_D_t_"


# --- preuves -----------------------------------------------------------------

@pytest.mark.parametrize("forme, statut, preuve, tunnel, attendu", [
    ("citation", "NT", "", False, []),
    ("citation", "C", "« mentions légales » (Boutique_A__cgv.txt)", False, []),
    ("citation", "NC", "absent: délai de rétractation (textes/Boutique_A__cgv.txt)", False, []),
    ("citation", "C", "absent: rien (Boutique_A__cgv.txt)", False, ["citation « … » manquante"]),
    ("citation", "NA", "rien (Boutique_A__cgv.txt)", False, ["citation « … » manquante (ou « absent: » pour un NC ou un NA)"]),
    ("citation", "C", "« x »", False, ["fichier .txt cité entre parenthèses manquant"]),
    ("citation", "C", "« x » (Boutique_B__cgv.txt)", False, ["fichier « Boutique_B__cgv.txt » qui n'est pas un fichier du site (préfixe Boutique_A)"]),
    ("citation", "C", "« " + "mot " * 26 + "» (Boutique_A__cgv.txt)", False, ["citation de plus de 25 mots"]),
    ("capture", "NC", "capture: Boutique_A__accueil__haut.jpg | texte illisible", False, []),
    ("capture", "NC", "capture: Boutique_A.jpg | paiement", False, ["fichier « Boutique_A.jpg » qui n'est pas un fichier du site (préfixe Boutique_A)"]),
    ("capture", "C", "capture: Boutique_A__accueil.html | vu", False, ["capture « Boutique_A__accueil.html » qui n'est pas une image (.jpg)"]),
    ("capture", "C", "dom: Boutique_A__accueil.html | <button>Menu principal</button>", False, ["preuve hors format (attendu « capture: fichier.jpg | ce qui est vu »)"]),
    ("dom_ou_capture", "C", "écran d'accueil", False, ["preuve hors format (attendu « capture: fichier.jpg | ce qui est vu » ou « dom: fichier | extrait »)"]),
    ("dom_ou_capture", "C", "dom: Boutique_A__accueil.html | « <button>Menu principal</button> »", False, []),
    ("dom_ou_capture", "C", "dom: Boutique_A__accueil.html | court", False, ["extrait DOM de 5 caractères (attendu 20 à 160)"]),
    ("dom_ou_capture", "NC", "dom: Boutique_A__accueil.html | <button>Menu principal</button>", True, ["règle du tunnel jugée hors de paiement/ (attendu NT)"]),
    ("dom_ou_capture", "NC", "dom: Boutique_A.txt | Frais de livraison offerts dès 50 euros", True, []),
    ("dom_ou_capture", "NC", "capture: paiement/Boutique_A__etape.jpg | étapes absentes", True, []),
    ("dom_ou_capture", "NC", "capture: Boutique_A.jpg | étapes absentes", True, []),
])
def test_erreurs_preuve(forme, statut, preuve, tunnel, attendu):
    assert vl.erreurs_preuve(forme, statut, preuve, "Boutique_A", None, tunnel) == attendu


def test_erreurs_preuve_fichier_absent():
    assert vl.erreurs_preuve("capture", "C", "capture: Boutique_A__x.jpg | vu", "Boutique_A", {"Boutique_A__y.jpg"}) == [
        "fichier « Boutique_A__x.jpg » introuvable dans le dossier hors dépôt"]
    assert vl.erreurs_preuve("capture", "C", "capture: Boutique_A__x.jpg | vu", "Boutique_A", {"Boutique_A__x.jpg"}) == []


def test_erreurs_entree():
    e = lambda num, k, v, regles3=None: vl.erreurs_entree(CFG[num], "Boutique A", k, v, SITES, None, regles3)
    assert vl.erreurs_entree(CFG["1"], "Boutique Z", "16", [], SITES) == ["site inconnu du parc (referentiel/parc.json)"]
    assert e("1", "3", ["C", "", "m"]) == ["règle « 3 » hors de la liste de la lecture Textes légaux"]
    assert e("3", "300", ["C", "", "m"]) == ["règle « 300 » hors du référentiel (1 à 245)"]
    assert e("3", "abc", ["C", "", "m"]) == ["règle « abc » hors du référentiel (1 à 245)"]
    assert e("3", "12", ["NT", "", "m"], {"Boutique A": ["13"]}) == ["règle « 12 » hors de la liste de la lecture DOM, captures et paiement"]
    assert e("3", "12", ["NT", "", "m"], {"Boutique A": [12]}) == []
    assert e("3", "12", ["NT", "", "m"], {}) == ["règle « 12 » hors de la liste de la lecture DOM, captures et paiement"]
    assert e("1", "16", ["C", "x"]) == ["entrée mal formée (attendu [statut, preuve, nature])"]
    assert e("1", "16", "C") == ["entrée mal formée (attendu [statut, preuve, nature])"]
    assert e("1", "16", ["C", 3, "m"]) == ["entrée mal formée (attendu [statut, preuve, nature])"]
    assert e("1", "16", ["OK", "", "m"]) == ["statut « OK » hors de C, NC, NA, NT"]
    assert e("1", "16", ["C", "« oui » (Boutique_A__cgv.txt)", "m", "citation vérifiée"]) == []
    assert e("3", "35", ["C", "dom: Boutique_A__accueil.html | <button>Menu principal</button>", "m"]) == [
        "règle du tunnel jugée hors de paiement/ (attendu NT)"]


def test_index_et_regles(tmp_path):
    assert vl.index_hors(None) is None and vl.index_hors(tmp_path) is None
    (tmp_path / "captures").mkdir()
    assert vl.index_hors(tmp_path) is None
    (tmp_path / "captures" / "a.jpg").write_text("x")
    (tmp_path / "captures" / "sous").mkdir()
    assert vl.index_hors(tmp_path) == {"a.jpg"}
    assert vl.regles_une_source(None) is None and vl.regles_une_source(tmp_path) is None
    ecrire_json(tmp_path / "regles_une_source.json", {"A": ["1"]})
    assert vl.regles_une_source(tmp_path) == {"A": ["1"]}


def test_lire_sortie(tmp_path):
    (tmp_path / "a.json").write_text("[1]")
    assert vl.lire_sortie(tmp_path / "a.json")[1] == ["le fichier doit être un objet {site: {règle: [statut, preuve, nature]}}"]


# --- valider_lectures.main ---------------------------------------------------

def test_valider_sans_sortie(racine, capsys):
    r = racine(vl)
    parc_test(r)
    assert vl.main([]) == 0
    assert "lecture 1 (Textes légaux) : aucune sortie" in capsys.readouterr().out
    assert vl.main(["--exiger", "1, 2"]) == 1
    assert "lecture 2 (Captures) : aucune sortie lecture_visuelle_lot*.json" in capsys.readouterr().out
    assert vl.main(["--exiger", "4"]) == 2
    assert vl.main(["--inconnu"]) == 2


def test_valider(racine, capsys, tmp_path):
    r = racine(vl)
    parc_test(r)
    hors = tmp_path / "hors"
    ecrire_json(hors / "regles_une_source.json", {"Boutique A": ["21"]})
    (hors / "captures").mkdir(parents=True)
    (hors / "captures" / "Boutique_A__accueil__haut.jpg").write_text("x")
    ancien = r / "resultats/sources-2026-11-10"
    ecrire_json(ancien / "lecture_visuelle_lot1.json", {"Boutique A": {"4": ["NC", "faux", "m"]}})
    ecrire_json(r / "resultats/sources-2026-11-12/lecture_visuelle_lot1.json", {"Boutique A": {
        "4": ["NC", "capture: Boutique_A__accueil__haut.jpg | texte gris", "m"]}})
    (r / "resultats/sources-2026-11-13").mkdir()
    ecrire_json(r / "resultats/sources-2026-11-12/lecture_dom_lot1.json", {"Boutique A": {
        "21": ["NC", "capture: Boutique_A__accueil__haut.jpg | menu caché", "m", "jugement visuel"]}})
    assert vl.main([str(hors), "--exiger", "2,3"]) == 0
    out = capsys.readouterr().out
    assert "✔ lecture 2 (Captures) : 1 fichier(s) dans sources-2026-11-12, 0 erreur(s)." in out and "lecture 1 (Textes légaux) : aucune sortie" in out
    ecrire_json(r / "resultats/sources-2026-11-12/lecture_dom_lot2.json", {"Boutique A": {
        "22": ["NC", "capture: Boutique_A__absent.jpg | x", "m"]}, "Boutique Z": {"1": ["C", "", "m"]}, "Boutique B": []})
    (r / "resultats/sources-2026-11-12/lecture_ia_lot1.json").write_text("{", encoding="utf-8")
    assert vl.main([str(hors)]) == 1
    out = capsys.readouterr().out
    assert "✖ lecture 3 (DOM, captures et paiement) : 2 fichier(s) dans sources-2026-11-12, 3 erreur(s)." in out
    assert "lecture_dom_lot2.json · Boutique A · règle 22 : règle « 22 » hors de la liste" in out
    assert "lecture_dom_lot2.json · Boutique Z · règle 1 : site inconnu du parc" in out
    assert "lecture_dom_lot2.json · Boutique B : attendu un objet" in out
    assert "lecture_ia_lot1.json : JSON illisible" in out and "4 erreur(s) : corriger" in out
    # sans <hors> : liste de la lecture 3 et fichiers non vérifiés ; <hors> vidé : on le dit
    (r / "resultats/sources-2026-11-12/lecture_ia_lot1.json").unlink()
    ecrire_json(r / "resultats/sources-2026-11-12/lecture_dom_lot2.json", {"Boutique A": {"22": ["NC", "capture: Boutique_A__absent.jpg | x", "m"]}})
    assert vl.main([]) == 0
    capsys.readouterr()
    assert vl.main([str(tmp_path / "vide")]) == 0
    assert "existence des fichiers cités non vérifiée" in capsys.readouterr().out


# --- preparer_lectures -------------------------------------------------------

def test_lots():
    assert pl.lots(["a", "b", "c", "d"], 3) == [(1, ["a", "b", "c"]), (2, ["d"])]


def test_preparer_parc_vide(racine, tmp_path, capsys):
    r = racine(pl)
    parc_test(r, ())
    assert pl.main([str(tmp_path)]) == 1 and "Parc vide" in capsys.readouterr().err
    assert pl.main([str(tmp_path), "--lecture", "4"]) == 2


def test_preparer(racine, tmp_path, capsys):
    r = racine(pl)
    parc_test(r, ("Boutique A", "Boutique B", "Boutique C", "Boutique D"))
    hors = tmp_path / "hors"
    for s in ("A", "B", "C", "D"):
        (hors / "textes").mkdir(parents=True, exist_ok=True)
        (hors / "textes" / f"Boutique_{s}__cgv.txt").write_text("x")
    (hors / "captures").mkdir()
    (hors / "captures" / "Boutique_A__accueil__haut.jpg").write_text("x")
    (hors / "protocoles").mkdir()
    (hors / "protocoles" / "16.md").write_text("protocole")
    (hors / "briefs").mkdir()
    (hors / "briefs" / "lecture2_lot9.md").write_text("ancien")
    # lectures 1 et 2 par défaut ; lecture 3 sans liste : pas proposée
    assert pl.main([str(hors), "--date", "2026-11-19"]) == 1
    out = capsys.readouterr().out
    assert "⚠ Lecture 2, Boutique B : entrée manquante" in out and "6 brief(s)" in out
    briefs = sorted(p.name for p in (hors / "briefs").glob("lecture*.md"))
    assert briefs == ["lecture1_lot1.md", "lecture1_lot2.md", "lecture2_lot1.md", "lecture2_lot2.md", "lecture2_lot3.md", "lecture2_lot4.md"]
    b1 = (hors / "briefs" / "lecture1_lot1.md").read_text(encoding="utf-8")
    sortie = r / "resultats" / "sources-2026-11-19" / "lecture_ia_lot1.json"
    assert f"`{sortie}`" in b1 and "Boutique C : préfixe de fichiers `Boutique_C`" in b1 and "Boutique D" not in b1
    assert "Bilan rendu : 15 lignes au plus." in b1 and f"{hors}/protocoles/" in b1
    assert "get_rule pour 2, 7, 8, 17," in b1 and "Protocoles déjà extraits" in b1 and "16." in b1
    assert str(hors / "textes" / "Boutique_A__cgv.txt") in b1
    b2 = (hors / "briefs" / "lecture2_lot2.md").read_text(encoding="utf-8")
    assert "aucun fichier trouvé" in b2 and "ATTENTION, entrées manquantes : captures/Boutique_B__*.jpg" in b2 and "Règles du tunnel" not in b2
    union = lire_json(hors / "briefs" / "regles_a_charger.json")
    assert 16 in union and 192 in union and union == sorted(set(union))
    # lecture 3 demandée sans liste
    assert pl.main([str(hors), "--lecture", "3"]) == 1
    assert "regles_une_source.json manque" in capsys.readouterr().err


def test_preparer_lecture3(racine, tmp_path, capsys):
    r = racine(pl)
    parc_test(r)
    hors = tmp_path / "hors"
    ecrire_json(hors / "regles_une_source.json", {"Boutique A": ["35", "12", "12"], "Boutique B": []})
    for d, f in (("dom", "Boutique_A__accueil.html"), ("captures", "Boutique_A__accueil.jpg"), ("paiement", "Boutique_A.txt")):
        (hors / d).mkdir(parents=True)
        (hors / d / f).write_text("x")
    (hors / "protocoles").mkdir()
    for k in ("12", "35"):
        (hors / "protocoles" / f"{k}.md").write_text("p")
    assert pl.main([str(hors), "--lecture", "3"]) == 0
    out = capsys.readouterr().out
    assert "Boutique B n'a aucune règle à une seule source" in out
    b3 = (hors / "briefs" / "lecture3_lot1.md").read_text(encoding="utf-8")
    assert "## Règles (2)\n\n12, 35" in b3 and "Règles du tunnel (35, 36" in b3 and "(si présent)" in b3 and "get_rule pour" not in b3
    assert f"sources-{date.today():%Y-%m-%d}" in b3 and "lecture_dom_lot1.json" in b3
    assert json.loads(b3.split("```json\n")[1].split("\n```")[0]) == {"Boutique A": {"12": ["C", "<preuve au format ci-dessus>", "lecture"]}}
    assert not (hors / "briefs" / "lecture3_lot2.md").exists()
