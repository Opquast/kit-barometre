"""Tests de lecture_critique.py (recoupement des sources et écarts)."""

from __future__ import annotations

from datetime import date

import pytest

import lecture_critique as lc
from conftest import ecrire_json, lire_json

ROBOT, PAGE, LH = lc.ROBOT, lc.PAGE, lc.LH


# --- analyse_outils ---------------------------------------------------------

@pytest.mark.parametrize("k, src, type_, statut", [
    ("69", {}, "faux négatif", "NC"),
    ("117", {ROBOT: "NC", "axe-core": "C"}, "divergence de critère", "NC"),
    ("118", {"IBM Equal Access": "NC"}, "faux négatif", "NC"),
    ("119", {}, "faux négatif", "NC"),
    ("136", {ROBOT: "NC"}, "faux positif", "C"),
    ("136", {"axe-core": "NC"}, "faux négatif", "NC"),
    ("136", {PAGE: "NC", LH: "NC"}, "faux négatif", "NC"),
    ("182", {}, "divergence de critère", "NC"),
    ("186", {}, "divergence de critère", "NC"),
    ("193", {}, "faux négatif", "NC"),
    ("226", {}, "faux positif", "C"),
    ("229", {LH: "NC"}, "écart à vérifier", "NC"),
    ("230", {LH: "C"}, "faux positif", "C"),
    ("229", {}, "faux positif", "NT"),
    ("236", {}, "faux négatif", "NC"),
])
def test_analyse_outils(k, src, type_, statut):
    typ, st, pq, reco = lc.analyse_outils(k, src)
    assert (typ, st) == (type_, statut) and pq and reco


def test_analyse_outils_sans_analyse():
    assert lc.analyse_outils("136", {"Lighthouse": "NC"}) is None
    assert lc.analyse_outils("999", {}) is None


def test_outils(racine):
    r = racine(lc)
    assert lc.dernier("resultats/rien-*") is None and lc.lire("resultats/rien-*/x.json") == {}
    ecrire_json(r / "resultats/reseau-2026-11-12/resultats.json", {"services": {"A": {
        "site": [{"rule_number": 1, "status": "conforme"}, {"rule_number": 1, "status": "non-conforme"}],
        "pages": [{"controles": [{"rule_number": 2, "status": "non-applicable"}, {"rule_number": 2, "status": "non-applicable"},
                                 {"rule_number": 3, "status": "conforme"}, {"rule_number": 3, "status": "non-applicable"},
                                 {"rule_number": 4, "status": "non-testé"}]}, {}]}}})
    ecrire_json(r / "resultats/reseau-2026-11-12-essai/resultats.json", {"services": {"B": {}}})
    assert lc.charger_outil("reseau") == {"A": {"1": "NC", "2": "NA", "3": "C"}}
    it = lc.item("écart", "1", "T", "a / b", "c", "p", "r", "ZZ")
    assert it["statut_lib"] == "ZZ" and it["base"] == []


# --- main -------------------------------------------------------------------

URL_A = "https://a.fr/"


def preparer(r, monkeypatch):
    monkeypatch.setattr(lc, "ECARTEES", {"8"})
    monkeypatch.setattr(lc, "EXCL_SITES", {"Boutique A": [7]})
    reg = lambda robot, statut="C", scripts=None, titre=None: {"robot": robot, "statut": statut, "scripts": scripts, "titre": titre}
    ecrire_json(r / "resultats/etat-2026-11-12/etat.json", {
        "sites": {
            "Boutique A": {"227": reg("NC", "C", "C", "T227"), "165": reg("NC"), "232": reg("C"), "103": reg("NC", "C"),
                           "137": reg("NC", "NT"), "192": reg("NC", "NT"), "153": reg("NC"), "10": reg("NC", "NT"),
                           "11": reg("NC", ""), "12": reg("C"), "7": reg("C"), "8": reg("C"), "13": reg(None)},
            "Boutique B": {"20": reg("NC", "NC", "NC")},
        },
        "emails": {"Klaviyo Boutique C": {
            "EM02": {"titre": "Alt", "ecrans": {"E1": ["C", ""], "E2": ["NC", ""]}},
            "EM06": {"titre": "Contraste", "ecrans": {"E3": ["C", ""]}},
            "EM10": {"titre": "Cible", "ecrans": {"E1": ["C", ""]}},
            "EM11": {"titre": "Libellé", "ecrans": {"E1": ["NC", ""]}},
            "EM12": {"titre": "Taille", "ecrans": {"E1": ["I", ""]}},
            "EM30": {"titre": "Autre", "ecrans": {"E1": ["C", ""]}},
            "EM25": {"titre": "Domaine", "ecrans": {"E1": ["C", ""], "E2": ["NT", ""]}},
        }}})
    ecrire_json(r / "resultats/contre-examen-2026-11-12/fiche.json", {"Boutique A": [
        {"regle": 165, "titre": "Focus", "decision_statut": "C", "constat_navigateur": "Focus visible."},
        {"regle": 5, "titre": "T5", "decision_statut": "NC", "constat_navigateur": ""},
        {"regle": 6, "titre": "T6", "decision_statut": "C", "constat_navigateur": ""},
        {"regle": 18, "titre": "T18", "decision_statut": None, "constat_navigateur": ""}]})
    ecrire_json(r / "resultats/reseau-2026-11-12/resultats.json", {"services": {"Boutique A": {"site": [
        {"rule_number": 227, "status": "conforme"}, {"rule_number": 10, "status": "conforme"}, {"rule_number": 9, "status": "non-conforme"},
        {"rule_number": 5, "status": "conforme"}, {"rule_number": 6, "status": "non-conforme"}]}}})
    ecrire_json(r / "resultats/page-2026-11-12/resultats.json", {"services": {"Boutique A": {"pages": [{"controles": [
        {"rule_number": 232, "status": "non-conforme"}, {"rule_number": 9, "status": "conforme"}]}]}}})
    ecrire_json(r / "resultats/axe-2026-11-12/resultats.json", {"sites": {"Boutique A": {"regles": {
        "label": {"elements": 2, "pages": 1}, "region": {"elements": 1, "pages": 1}}}}})
    ecrire_json(r / "resultats/outils-2026-11-12/pages.json", {"Boutique A": {"pages": {URL_A: {
        "gabarit": "Accueil (FR)", "ibm": {"par_regle": {"a_text_purpose": 1, "autre_regle": 2}},
        "lighthouse": {"audits": {"is-on-https": 0.5, "meta-description": 1.0, "inconnu": 0.1, "viewport": None}}}}},
        "Boutique B": {"pages": {"https://b.fr/": {"gabarit": "Accueil"}}}})
    ecrire_json(r / "resultats/outils-2026-11-12/j2.json", {"Boutique A": {
        "pages": {URL_A: {"pa11y": {"par_code": {"WCAG2AA.1_1_1.H37": 3, "Autre.Code": 1}}}, "x": {}},
        "sitemap": {"bien_forme": True, "statut_http": 200}}})
    ecrire_json(r / "resultats/outils-2026-11-12/en_ligne.json", {
        "Boutique A": {"ssllabs": {"notes": ["A", "C"]},
                       "observatory": {"penalites": [["a", "hsts-short", -10], ["b", "csp-none", -20], ["c", "sri-not-implemented-x", 0],
                                                     ["d", "x-frame-none", -5], ["e", "cookies-x", -5], ["f", "referrer", 5]]},
                       "nu": {URL_A: {"erreurs": 3, "principales": [["Duplicate ID x", 2], ["Autre", 1]]},
                              "https://a.fr/v": {"gabarit": "Vide", "erreur": "page non lue par le validateur"}}},
        "Boutique B": {"ssllabs": {}, "observatory": {"penalites": []},
                       "nu": {"https://b.fr/": {"erreurs": 1, "principales": [["Autre", 1]]}}}})
    ecrire_json(r / "resultats/parcours-2026-11-12/parcours.json", {"Boutique A": {"paiement": {
        "cases_precochees": ["Recevoir nos offres par e-mail", "Adresse de facturation"]}}})
    ecrire_json(r / "resultats/releve-2026-11-12/decisions.json", {"Boutique A": {
        "153": ["C", "accès immédiat", "mesure"], "11": ["C", "relevé", "mesure"], "137": ["NC", "libellé", "lecture"],
        "abc": ["C", "", "mesure"], "14": ["NT", "", "mesure"], "7": ["C", "", "mesure"]}})
    ecrire_json(r / "resultats/sources-2026-11-12/pages.json", {"Boutique A": {URL_A: {
        "_gabarit": "Accueil", "15": [["NC", "absent", "Playwright (événements popup)"]]}}})
    ecrire_json(r / "resultats/sources-2026-11-12/html.json", {"Boutique A": {URL_A: {
        "_gabarit": "Accueil", "_non_teste": "", "15": ["C", "lien", "HTML brut (sans JavaScript)"]}}})
    ecrire_json(r / "resultats/sources-2026-11-12/tiers.json", {"Boutique A": {URL_A: {
        "_gabarit": "Accueil", "103": [["C", "titre court", "html-validate"]], "192": [["C", "", "Sa11y"]], "137": [["C", "", "Sa11y"]]}}})
    ecrire_json(r / "resultats/sources-2026-11-12/html2.json", {"Boutique A": {URL_A: {"_g": 1, "1": ["C", "flux", "HTML brut et CSS (sans JavaScript)"]}}})
    ecrire_json(r / "resultats/sources-2026-11-12/curl.json", {"Boutique A": {"_x": 1, "135": ["NC", "langue", "curl"]}})
    ecrire_json(r / "resultats/sources-2026-11-12/panier.json", {"Boutique A": {"34": ["C", "", "API panier Shopify (cart.js)"]}})
    ecrire_json(r / "resultats/aria-2026-11-12/resultats.json", {"services": {"Boutique A": {"pages": [{"controles": [
        {"rule_number": 185, "status": "non-conforme", "comment": "axe-core aria-hidden-focus, IBM aria_hidden_nontabbable (2)"},
        {"rule_number": 185, "status": "non-conforme", "comment": "autre"},
        {"rule_number": 185, "status": "conforme", "comment": "Aucun (axe-core et IBM)"},
        {"rule_number": 185, "status": "conforme", "comment": "Aucun"},
        {"rule_number": 185, "status": "non-testé", "comment": ""},
        {"rule_number": 244, "status": "conforme", "comment": ""}]}]}}})
    ecrire_json(r / "resultats/sources-2026-11-12/shopify.json", {
        "Boutique A": {"_fini": True, "223": ["C", "Code 404, 30 Ko", "HTML brut de la page 404"], "47": ["C", "pays", "Shopify meta.json"]},
        "Boutique B": {"223": ["NC", "sans code", "HTML brut de la page 404"]}})
    ecrire_json(r / "referentiel/parc.json", {"responsable": "Camille", "sites": [{"nom": "Boutique A"}, {"nom": "Boutique B"}]})
    ecrire_json(r / "resultats/sources-2026-11-12/lecture_ia_lot1.json", {"Boutique A": {
        "16": ["C", "« cité » (Boutique_A__cgv.txt)", "m", "citation vérifiée"], "17": ["C", "« pas trouvé » (Boutique_A__cgv.txt)", "m", "citation introuvable"],
        "22": ["C", "court", "m"], "18": ["NC", "absent: hors liste (Boutique_A__cgv.txt)", "m"]},
        "Boutique Inconnue": {"16": ["C", "« cité » (Boutique_Inconnue__cgv.txt)", "m", "citation vérifiée"]}, "Boutique B": "pas un objet"})
    (r / "resultats/sources-2026-11-12/lecture_ia_lot2.json").write_text("{pas du json", encoding="utf-8")
    ecrire_json(r / "resultats/sources-2026-11-12/lecture_dom_lot1.json", {"Boutique A": {
        "21": ["NC", "dom: Boutique_A__accueil.html | <button class=\"menu\">Menu</button>", "m", "extrait vérifié"],
        "22": ["C", "", "m", "preuve absente"], "23": ["C", "dom: Boutique_A__accueil.html | <button class=\"x\">Ok</button>", "m"]}})
    ecrire_json(r / "resultats/sources-2026-11-12/lecture_visuelle_lot1.json", {"Boutique A": {
        "4": ["NC", "capture: Boutique_A__accueil__haut.jpg | texte gris clair illisible", "m"], "24": ["NC", "capture", "m"]}})
    ecrire_json(r / "resultats/email-2026-11-12/outils.json", {
        "E1": {"axe": {"violations": [{"regle": "image-alt", "elements": 2}]}}, "E2": {"axe": {"violations": []}}, "E3": {"axe": {"violations": []}}})
    ecrire_json(r / "resultats/email-2026-11-12/checkdmarc.json", {"domaines": {
        "exemple.fr": {"spf": {"valide": True}, "dmarc": {"valide": True}}, "mail.exemple.fr": {"spf": {"valide": False}}}})
    ecrire_json(r / "resultats/email-2026-11-12/sources_secondes.json", {
        "E1": {"_note": [], "EM10": [["NC", "cible trop petite", "IBM"], ["XX", "", "rien"]], "EM99": [["NC", "", "IBM"]],
               "EM12": [["NC", "petit", "Playwright"], ["C", "", "IBM"]]},
        "E9": {"EM10": [["NC", "", "IBM"]]}})
    ecrire_json(r / "resultats/email-2026-11-12/lecture_ia_independante.json", {
        "E1": {"EM10": ["C", "ok", "Lecture IA"], "EM11": ["C", "cité"], "EM12": ["C", "", "IBM"]}})


def test_lecture_critique(racine, monkeypatch, capsys):
    r = racine(lc)
    preparer(r, monkeypatch)
    lc.main()
    out = lire_json(r / "resultats" / f"lecture-critique-{date.today():%Y-%m-%d}" / "lecture.json")
    a = out["Boutique A"]
    ecarts = {e["regle"]: e for e in a["ecarts"]}
    assert ecarts["227"]["entre"] == "robot / scripts" and ecarts["227"]["statut"] == "C"
    assert ecarts["165"]["entre"] == "robot / contre-examen navigateur" and "Focus visible" in ecarts["165"]["constat"]
    assert ecarts["232"]["type"] == "faux négatif"
    assert ecarts["103"]["statut"] == "C"
    assert ecarts["137"]["statut"] == "NC"
    assert ecarts["192"]["statut"] == "NC"
    assert ecarts["153"].get("a_arbitrer") is True and "a_arbitrer" not in ecarts["192"]
    assert ecarts["5"]["type"] == "faux négatif" and ecarts["5"]["titre"] == "T5"
    assert ecarts["6"]["type"] == "faux positif" and ecarts["6"]["statut"] == "C"
    assert ecarts["9"]["type"] == "faux négatif" and ecarts["9"]["titre"] == "Règle 9"
    assert ecarts["10"]["type"] == "écart à vérifier" and ecarts["10"]["statut"] == "NT"
    assert ecarts["11"]["type"] == "écart" and ecarts["11"]["statut"] == "NT"
    assert "12" not in ecarts
    assert ecarts["33"]["type"] == "inattendu pertinent" and "Recevoir nos offres" in ecarts["33"]["constat"]
    assert ecarts["Nu"]["constat"].startswith("Le validateur W3C a renvoyé 0 erreur et 0 avertissement sur 1 page(s) (Vide)")
    assert ecarts["-"]["type"] == "limite d'outil"
    assert [x["regle"] for x in a["trois_interessants"]][2] == "33"
    rec = a["recoupement"]
    assert rec["185"]["axe-core"] == "NC" and rec["185"]["IBM Equal Access"] == "NC" and "axe-core et IBM (aria-hidden, tableaux)" not in rec["185"]
    assert rec["236"]["Validateur Nu (W3C)"] == "NC"
    assert rec["197"]["Qualys SSL Labs"] == "NC" and rec["200"]["Lighthouse"] == "NC" and rec["3"]["Lighthouse"] == "C"
    assert rec["199"]["MDN HTTP Observatory"] == "NC" and rec["214"]["MDN HTTP Observatory"] == "NC"
    assert rec["220"]["Sitemap (xmllint)"] == "C" and rec["222"]["HTML brut de la page 404"] == "C"
    assert rec["16"]["Lecture IA indépendante (probabiliste)"] == "C" and "17" not in rec and "18" not in rec
    assert rec["21"]["Lecture IA du DOM et des captures (probabiliste)"] == "NC" and "22" not in rec and "23" not in rec
    assert rec["4"]["Lecture visuelle IA des captures (probabiliste)"] == "NC" and "24" not in rec
    assert "Contre-examen (validé par Camille)" in rec["6"] and "validé par Camille" in ecarts["6"]["pourquoi"]
    sortie_ = capsys.readouterr().out
    assert "Lecture 1 (Textes légaux) : 5 entrée(s) invalide(s)" in sortie_ and "Lecture 2 (Captures) : 1 entrée(s)" in sortie_
    assert "14" not in rec and rec["118"]["Pa11y (HTML_CodeSniffer)"] == "NC"
    assert a["statut_sources"]["12"] == "C" and a["statut_sources"]["232"] is None
    assert "7" not in a["sources_par_regle"] and "8" not in a["sources_par_regle"] and "abc" in a["sources_par_regle"]
    b = out["Boutique B"]
    assert [x["regle"] for x in b["ecarts"]] == ["-"] and b["accords_robot_scripts"] == 1 and b["trois_interessants"] == []
    assert "222" not in b["recoupement"]
    em = {(e["regle"], e["constat"].split(" :")[0]): e for e in out["_emails"]["Klaviyo Boutique C"]["ecarts"]}
    assert em[("EM02", "Sur E1")]["type"] == "faux négatif"
    assert em[("EM02", "Sur E2")]["type"] == "écart à vérifier" and em[("EM02", "Sur E2")]["statut"] == "NC"
    assert em[("EM10", "Sur E1")]["statut"] == "NC" and "cible trop petite" in em[("EM10", "Sur E1")]["constat"]
    assert em[("EM12", "Sur E1")]["statut"] == "NC"
    assert em[("EM25", "Sur E1")]["type"] == "limite d'outil"
    sources = out["_emails"]["Klaviyo Boutique C"]["sources_par_critere"]
    assert sources["EM30"] == ["Checklist (script et IA)"] and "axe-core" in sources["EM06"] and "IBM" in sources["EM10"]
    assert "Boutique A" in sortie_


def test_lecture_critique_minimale(racine, monkeypatch):
    r = racine(lc)
    monkeypatch.setattr(lc, "ECARTEES", set())
    monkeypatch.setattr(lc, "EXCL_SITES", {})
    ecrire_json(r / "resultats/etat-2026-11-12/etat.json", {"sites": {"Boutique Z": {"1": {"robot": None, "statut": "C", "scripts": None}}},
                                                           "emails": {"Klaviyo": {"EM25": {"titre": "D", "ecrans": {"E1": ["C", ""]}}}}})
    lc.main()
    out = lire_json(r / "resultats" / f"lecture-critique-{date.today():%Y-%m-%d}" / "lecture.json")
    assert [x["regle"] for x in out["Boutique Z"]["ecarts"]] == ["-"]
    assert out["_emails"]["Klaviyo"]["ecarts"] == []
