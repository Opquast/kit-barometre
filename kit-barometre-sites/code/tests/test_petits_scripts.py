"""Tests de verifier_citations.py, import_esm.py et controles_aria.py."""

from __future__ import annotations

import csv
import sys
from datetime import date

import controles_aria
import import_esm
import verifier_citations as vc
from aide_parc import poser_parc
from conftest import ecrire_json, lire_json


# --- verifier_citations -----------------------------------------------------

def test_norm():
    assert vc.norm("L’Été — Ça !") == "l'été ça"


def test_verifier_citations_textes_absents(racine, tmp_path, monkeypatch, capsys):
    r = racine(vc)
    ecrire_json(r / "resultats/sources-2026-11-19/lecture_ia_lot1.json", {"Ma boutique": {"1": ["C", "« x »", "m"]}})
    textes = tmp_path / "hors" / "textes"
    textes.mkdir(parents=True)
    monkeypatch.setattr(sys, "argv", ["vc", str(textes)])
    vc.main()
    assert "vérification précédente conservée" in capsys.readouterr().out


def test_verifier_citations_ia_et_dom(racine, tmp_path, monkeypatch):
    r = racine(vc)
    hors = tmp_path / "hors"
    textes = hors / "textes"
    textes.mkdir(parents=True)
    (textes / "Ma_boutique__accueil.txt").write_text("Livraison offerte dès 50 euros partout en France", encoding="utf-8")
    (hors / "dom").mkdir()
    (hors / "dom" / "accueil.html").write_text("<p>Mentions légales du site</p>", encoding="utf-8")
    ia = ecrire_json(r / "resultats/sources-2026-11-19/lecture_ia_lot1.json", {"Ma boutique": {
        "1": ["C", "« Livraison offerte dès 50 euros »", "m", "ancien"],
        "2": ["C", "« Retour gratuit sous 30 jours »", "m"],
        "3": ["NC", "rien", "m"],
        "4": ["C", "sans citation", "m"],
        "5": ["C", "« Livraison offerte … partout en France »", "m"],
    }})
    dom = ecrire_json(r / "resultats/sources-2026-11-19/lecture_dom_lot1.json", {"Ma boutique": {
        "10": ["C", "dom: dom/accueil.html | Mentions légales", "m"],
        "11": ["NC", "dom: accueil.html | Texte absent de la page", "m"],
        "12": ["NA", "capture: rien à voir", "m"],
        "13": ["C", "aucune preuve", "m"],
        "14": ["NT", "", "m"],
        "15": ["C", "dom: disparu.html | Bonjour", "m", "extrait vérifié"],
        "16": ["C", "dom: disparu.html | Bonjour", "m"],
    }})
    monkeypatch.setattr(sys, "argv", ["vc", str(textes)])
    vc.main()
    d = lire_json(ia)["Ma boutique"]
    assert d["1"][3] == "citation vérifiée" and len(d["1"]) == 4
    assert d["2"][3] == "citation introuvable"
    assert d["3"] == ["NC", "rien", "m"]
    assert d["4"][3] == "citation introuvable"
    assert d["5"][3] == "citation vérifiée"
    d = lire_json(dom)["Ma boutique"]
    assert d["10"][3] == "extrait vérifié"
    assert d["11"][3] == "extrait introuvable"
    assert d["12"][3] == "jugement visuel"
    assert d["13"][3] == "preuve absente"
    assert d["14"] == ["NT", "", "m"]
    assert d["15"][3] == "extrait vérifié"
    assert d["16"][3] == "extrait introuvable"


# --- import_esm -------------------------------------------------------------

def test_code_et_titre_page():
    assert import_esm.code_page("BM", "Accueil (FR)") == ""
    assert import_esm.code_page("BM", "Fiche produit (variante)") == "BM-FICHE-PRODUIT"
    assert import_esm.code_page("BM", "Page/légale") == "BM-PAGELÉGALE"
    assert import_esm.titre_page("Accueil") == "Accueil"
    assert import_esm.titre_page("Panier") == "Panier"


def test_import_esm_main(racine, tmp_path, monkeypatch, capsys):
    r = poser_parc(racine, import_esm)
    (r / "scripts" / "ecrans_en_ligne.csv").write_text(
        "service,gabarit,url\nBoutique A,Fiche produit,https://a.fr/p\n", encoding="utf-8")
    dossier = tmp_path / "reseau"
    ecrire_json(dossier / "resultats.json", {
        "meta": {"date": "2026-11-12T10:00:00", "version": "1.2"},
        "services": {"Boutique A": {
            "site": [{"rule_number": 1, "status": "conforme", "comment": "ok", "evidence": "mailto:x@y.fr"}],
            "pages": [
                {"gabarit": "Accueil", "url": "https://a.fr/", "controles": [
                    {"rule_number": 2, "status": "non-testé", "comment": "?"}]},
                {"gabarit": "Produit", "url": "https://a.fr/p", "controles": [
                    {"rule_number": 3, "status": "non-conforme", "comment": "ko"}]},
                {"gabarit": "Panier", "url": "https://a.fr/c"},
            ]},
            "Boutique Z": {"site": [], "pages": [{"gabarit": "Accueil", "url": "https://z.fr/"}]}}})
    monkeypatch.setattr(sys, "argv", ["import_esm", str(dossier)])
    import_esm.main()
    lignes = list(csv.reader((dossier / "import-esm-WEB-BOUTIQUEA.csv").open(encoding="utf-8")))
    assert lignes[0] == import_esm.ENTETE
    assert lignes[1][:3] == ["WEB-BOUTIQUEA", "opquast-1", "C"]
    assert "mailto:[masqué]" in lignes[1][3]
    assert lignes[2][2:5] == ["NC", "[controles_reseau.py v1.2] ko", "BM-FICHE-PRODUIT"]
    assert len(lignes) == 3 and lignes[1][7] == "MLU"
    out = capsys.readouterr().out
    assert "2 lignes" in out and "Boutique Z : absent de referentiel/parc.json" in out
    assert not (dossier / "import-esm-WEB-BOUTIQUEZ.csv").exists()


def test_import_esm_dossier_par_defaut(racine, monkeypatch):
    racine(import_esm)
    monkeypatch.setattr(sys, "argv", ["import_esm"])
    lu = []
    monkeypatch.setattr(import_esm.json, "loads", lambda t: lu.append(t) or {
        "meta": {"date": "2026", "version": "1"}, "services": {}})
    monkeypatch.setattr(import_esm.Path, "read_text", lambda self, encoding=None: "{}")
    import_esm.main()
    assert lu and set(lu) == {"{}"}  # parc.json et resultats.json du dossier par défaut


# --- controles_aria ---------------------------------------------------------

def test_dernier_absent(racine):
    racine(controles_aria)
    assert controles_aria.dernier("resultats/rien-*/x.json") == {}


def test_controles_aria_main(racine, capsys):
    r = racine(controles_aria)
    base = "https://www.exemple-boutique.fr"
    ecrire_json(r / "resultats/axe-2026-11-19/resultats.json", {"sites": {"Ma boutique": {"pages": [
        {"chemin": "/", "teste": True, "violations": [{"regle": "aria-hidden-focus"}]},
        {"chemin": "/collections/all", "teste": True, "violations": []},
        {"chemin": "/search?q=exemple", "teste": False},
    ]}}})
    ecrire_json(r / "resultats/outils-2026-11-19/pages.json", {"Ma boutique": {"pages": {
        f"{base}/": {"ibm": {"par_regle": {"aria_hidden_nontabbable": 2, "table_layout_linearized": 1}}},
        f"{base}/products/exemple": {"ibm": {"par_regle": {}}},
        f"{base}/cart": {"ibm": {"par_regle": {}}},
    }}})
    ecrire_json(r / "resultats/releve-2026-11-19/releve.json", {"Ma boutique": {
        f"{base}/collections/all": {"tableaux": [1, 2]},
        "pages": {f"{base}/cart": {"tableaux": [1]}},
    }})
    controles_aria.main()
    sortie = r / "resultats" / f"aria-{date.today():%Y-%m-%d}" / "resultats.json"
    pages = {p["url"]: {c["rule_number"]: c for c in p["controles"]} for p in lire_json(sortie)["services"]["Ma boutique"]["pages"]}
    accueil = pages[f"{base}/"]
    assert accueil[185]["status"] == "non-conforme" and "axe-core" in accueil[185]["comment"] and "IBM" in accueil[185]["comment"]
    assert accueil[244]["status"] == "non-conforme"
    coll = pages[f"{base}/collections/all"]
    assert coll[185]["status"] == "conforme" and coll[185]["comment"].startswith("Aucun") and "IBM" not in coll[185]["comment"]
    assert coll[244] == {"rule_number": 244, "status": "non-testé", "comment": "2 tableau(x), linéarisation non vérifiée."}
    prod = pages[f"{base}/products/exemple"]
    assert prod[185]["status"] == "conforme" and "(IBM)" in prod[185]["comment"]
    assert prod[244]["status"] == "non-applicable" and "IBM sans défaut" in prod[244]["comment"]
    assert pages[f"{base}/cart"][244]["status"] == "conforme"
    recherche = pages[f"{base}/search?q=exemple"]
    assert recherche[185]["status"] == "non-testé"
    assert recherche[244]["status"] == "non-testé"
    assert "Ma boutique" in capsys.readouterr().out


def test_controles_aria_sans_mesures(racine):
    r = racine(controles_aria)
    ecrire_json(r / "resultats/releve-2026-11-19/releve.json", {"Ma boutique": ["pas un dictionnaire"]})
    (r / "scripts" / "ecrans_en_ligne.csv").write_text("service,gabarit,url\nMa boutique,Accueil,https://x.fr\n", encoding="utf-8")
    controles_aria.main()
    sortie = lire_json(r / "resultats" / f"aria-{date.today():%Y-%m-%d}" / "resultats.json")
    c = sortie["services"]["Ma boutique"]["pages"][0]["controles"]
    assert [x["status"] for x in c] == ["non-testé", "non-testé"]
