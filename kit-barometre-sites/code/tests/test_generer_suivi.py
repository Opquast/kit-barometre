"""Tests de generer_suivi.py (page de suivi) et exporter_csv.py (CSV du baromètre)."""

from __future__ import annotations

import csv
from datetime import date
from types import SimpleNamespace

import pytest

import exporter_csv as ex
import generer_suivi as g
from aide_parc import PARC_ORIGINE, poser_parc
from conftest import ecrire_json, lire_json

GLOBAUX = ("ETAT", "EXEMPLES", "LECTURE", "FICHE", "OUTILS_PAGES", "OUTILS_LIGNE", "PARCOURS_RES", "RELEVE", "AUD", "RECOS",
           "METH", "RAISON", "EXCLUSIONS", "AXE", "COMPLEMENTS")
PARC_SUIVI = dict(PARC_ORIGINE, sites=[x for x in PARC_ORIGINE["sites"] if x["nom"] in ("Boutique A", "Boutique C", "Boutique F")])
ECRANS = ("service,gabarit,url\nBoutique A,Accueil,https://a.fr/\nBoutique A,Recherche,https://a.fr/search?q=x\n"
          "Boutique C,Produit,https://c.fr/products/p\n")
PAGE_HTML = ('<html><head><style>body{} /* Onglets */ .ancien{} @media (prefers-reduced-motion: reduce){}</style></head>'
             '<body><div class="wrap">ancien</div></body></html>')
CHECKLIST = ("id,theme,critere,verification,regle_opquast,source\n"
             "EM02,Accessibilité,Alternatives,script,118,W3C\nEM10,Accessibilité,Cibles,IA,,Klaviyo\n"
             "EM35,Mode sombre,Couleurs,IA,,Can I Email\nEM40,Mode sombre,Logo,IA,,Litmus\n")


def regle(statut, titre="Titre", scripts=None, robot=None, sources=None, pages_nc=None, reco="", methode="réseau", theme="Sécurité"):
    return {"titre": titre, "theme": theme, "methode": methode, "statut": statut, "scripts": scripts, "robot": robot,
            "pages_nc": pages_nc or [], "determinant": [f"preuve {statut}"],
            "sources": sources if sources is not None else [{"nom": "Audit scripts", "url": "https://esm/x", "statut": statut}],
            "recommandation": reco}


@pytest.fixture
def gs(racine, monkeypatch):
    r = poser_parc(racine, g, ex, donnees=PARC_SUIVI)
    for nom in GLOBAUX:
        monkeypatch.setattr(g, nom, {})
    for nom in ("FAIT", "A_FAIRE", "LIENS"):
        monkeypatch.setattr(g, nom, [])
    (r / "scripts" / "ecrans_en_ligne.csv").write_text(ECRANS, encoding="utf-8")
    monkeypatch.setattr(g, "SERVICES", g.construire_services())
    monkeypatch.setattr(g, "PAGE", r / "suivi-barometre.html")
    monkeypatch.setattr(g, "RESEAU_DIR", r / "resultats")
    monkeypatch.setattr(g, "git_log", lambda: [("abc123", "12/11 10:00", "Fusion de la branche"), ("def456", "12/11 11:00", "Ajout")])
    (r / "suivi-barometre.html").write_text(PAGE_HTML, encoding="utf-8")
    (r / "referentiel/checklist-email.csv").write_text(CHECKLIST, encoding="utf-8")
    return r


def preparer(r):
    a = {
        "1": regle("C", scripts="C", robot="C"), "2": regle("NC", scripts="NC", robot="C", pages_nc=["Accueil"], reco="Corriger 2"),
        "3": regle("NA", sources=[]), "5": regle("NT", robot="NT", methode="manuel"), "16": regle("NT"), "17": regle("NT"),
        "18": regle("NC", robot="NC", methode="manuel"), "19": regle("C"), "135": regle("C"), "136": regle("C"),
        "212": regle("NC", scripts="NC"), "20": regle("NT"),
    }
    c = {"1": regle("C")}
    y = {"1": regle("C")}
    emails = {"Klaviyo Boutique C": {
        "EM02": {"titre": "Alternatives", "theme": "Accessibilité", "statut": "NC", "recommandation": "Ajouter alt",
                 "ecrans": {"BOUTIQUEC-EM-POPUP": ["NC", "image sans alt"], "BOUTIQUEC-EM-FOOTER": ["NT", ""]},
                 "source": {"nom": "Audit e-mail", "url": "https://esm/e"}},
        "EM10": {"titre": "Cibles", "theme": "Accessibilité", "statut": "I", "recommandation": "",
                 "ecrans": {"BOUTIQUEC-EM-POPUP": ["I", "à juger"]}, "source": {"nom": "Audit e-mail", "url": "https://esm/e"}},
        "EM35": {"titre": "Couleurs", "theme": "Mode sombre", "statut": "C", "recommandation": "",
                 "ecrans": {"BOUTIQUEC-EM-POPUP": ["C", "ok"], "BOUTIQUEC-EM-FOOTER": ["I", ""]}, "source": {"nom": "Audit e-mail", "url": "https://esm/e"}},
    }}
    ecrire_json(r / "resultats/etat-2026-11-12/etat.json", {"date": "2026-11-12", "sites": {"Boutique A": a, "Boutique C": c, "Boutique Y": y}, "emails": emails})
    ecrire_json(r / "resultats/reseau-2026-11-05/resultats.json", {"services": {"Boutique C": {
        "site": [], "pages": [{"gabarit": "Panier", "statut_http": 429, "controles": []}]}}})
    ecrire_json(r / "resultats/reseau-2026-11-12/resultats.json", {"services": {"Boutique A": {
        "site": [{"rule_number": 198, "status": "conforme", "comment": "ok"}, {"rule_number": 217, "status": "non-conforme", "comment": "p=none"}],
        "pages": [{"gabarit": "Accueil", "statut_http": 200, "controles": [{"rule_number": 199, "status": "non-conforme", "comment": "court"}]},
                  {"gabarit": "Panier", "statut_http": 429, "controles": []}]}}})
    ecrire_json(r / "resultats/axe-2026-11-12/resultats.json", {"sites": {"Boutique A": {
        "pages_testees": 2, "pages_non_testees": 1, "regles_en_violation": 2, "regles_critiques": 1, "elements_en_defaut": 5,
        "regles": {"image-alt": {"gravite": "critical", "criteres": ["1.1.1"], "pages": 2, "elements": 3}},
        "pages": [{"teste": True, "regles_respectees": 40, "violations": [1, 2]}, {"teste": False}]}}})
    ecrire_json(r / "resultats/contre-examen-2026-11-12/fiche.json", {
        "Boutique A": [{"regle": 5, "titre": "Abréviations", "robot": "NC", "robot_constat": "sigle", "constat_navigateur": "ok",
                        "decision_statut": "C", "decision_motif": "sigles expliqués"},
                       {"regle": 18, "titre": "Compte", "robot": "NT", "robot_constat": "", "constat_navigateur": "",
                        "decision_statut": None, "decision_motif": "parcours de Mattea"},
                       {"regle": 999, "titre": "Inconnue", "robot": None, "constat_navigateur": "", "decision_statut": "NC", "decision_motif": "x"}],
        "Boutique Z": [{"regle": 1, "titre": "x", "robot": None, "constat_navigateur": "", "decision_statut": "C", "decision_motif": ""}],
        "Boutique Y": [{"regle": 1, "titre": "x", "robot": None, "constat_navigateur": "", "decision_statut": "NC", "decision_motif": "m"}]})
    ecrire_json(r / "resultats/releve-2026-11-12/decisions.json", {
        "Boutique A": {"1": ["C", "déjà", "mesure"], "4": ["NC", "date", "mesure"], "6": ["C", "lu", "lecture"], "8": ["NC", "x", "mesure"]},
        "Boutique Z": {"4": ["C", "", "mesure"]}})
    ecrire_json(r / "resultats/lecture-critique-2026-11-12/lecture.json", {
        "Boutique A": {"accords_robot_scripts": 3,
                       "ecarts": [
                           {"type": "faux positif", "regle": "19", "titre": "T19", "entre": "robot / scripts", "constat": "c", "pourquoi": "p",
                            "recommandation": "Reco", "statut": "NC", "statut_lib": "non conforme", "a_arbitrer": True,
                            "base": [["Script réseau (controles_reseau.py)", "C"], ["Opquast basics (robot)", "NC"], ["Parcours réel", "x"], ["Autre", None]]},
                           {"type": "faux négatif", "regle": "2", "titre": "T2", "entre": "validateur Nu", "constat": "c", "pourquoi": "p",
                            "recommandation": "", "statut": "C", "statut_lib": "conforme", "base": []},
                           {"type": "inattendu pertinent", "regle": "33", "titre": "T33", "entre": "parcours réel (paiement)", "constat": "c",
                            "pourquoi": "p", "recommandation": "", "statut": "NC", "statut_lib": "non conforme", "base": []},
                           {"type": "type inconnu", "regle": "-", "titre": "Mention", "entre": "eServices Manager", "constat": "c", "pourquoi": "p",
                            "recommandation": "", "statut": "", "statut_lib": "sans objet", "base": []},
                           {"type": "écart", "regle": "212", "titre": "T212", "entre": "inconnu", "constat": "c", "pourquoi": "p",
                            "recommandation": "", "statut": "NC", "statut_lib": "non conforme", "base": [["Opquast basics (robot)", "NC"]]},
                           {"type": "écart", "regle": "136", "titre": "T136", "entre": "x", "constat": "c", "pourquoi": "p",
                            "recommandation": "", "statut": "NC", "statut_lib": "non conforme", "base": []}],
                       "trois_interessants": [],
                       "statut_sources": {"16": "NC", "17": "C", "5": "C", "1": None, "20": "C"},
                       "sources_par_regle": {"16": ["Sa11y"], "17": ["Sa11y", "Relevé navigateur (Claude)"], "1": ["axe-core", "Lighthouse"],
                                             "2": [], "abc": []},
                       "recoupement": {"1": {"axe-core": "C", "Lighthouse": "NC", "Inconnu": "C", "IBM Equal Access": "NT"},
                                       "2": {"Sa11y": "NA", "Siteimprove Alfa": "NA"}, "17": {"Sa11y": "C", "Relevé navigateur (Claude)": "C"},
                                       "136": {"IBM Equal Access": "C", "axe-core": "NC"}, "abc": {"curl": "C"}}},
        "_emails": {"Klaviyo Boutique C": {
            "ecarts": [{"type": "faux négatif", "regle": "EM02", "titre": "Alternatives", "constat": "Sur BOUTIQUEC-EM-FOOTER : axe relève",
                        "pourquoi": "p", "recommandation": "r", "statut": "NC", "statut_lib": "non conforme", "base": [["axe-core", "NC"], ["Checklist", "x"]]},
                       {"type": "faux négatif", "regle": "EM02", "titre": "Alternatives", "constat": "Sur BOUTIQUEC-EM-POPUP : rien",
                        "pourquoi": "p", "recommandation": "r", "statut": "NC", "statut_lib": "non conforme", "base": []},
                       {"type": "nouveau", "regle": "EM99", "titre": "Autre", "constat": "pas de code", "pourquoi": "p",
                        "recommandation": "", "statut": "C", "statut_lib": "conforme", "base": []}],
            "recoupement": {"EM10": {"BOUTIQUEC-EM-POPUP": {"Checklist (script et IA)": "I", "IBM": "C"}},
                            "EM02": {"BOUTIQUEC-EM-POPUP": {"Checklist (script et IA)": "NC", "IBM": "C"}, "ABSENT": {"IBM": "C"}},
                            "EM35": {"BOUTIQUEC-EM-FOOTER": {"Checklist (script et IA)": "I", "IBM": "C", "axe-core": "NC"}},
                            "EM99": {"X": {}}}}},
        })
    pages = {"https://a.fr/": {"gabarit": "Accueil (FR)", "ibm": {"violations": 12, "regles": 3, "par_regle": {"img_alt_valid": 2, "svg_graphics_labelled": 1, "inconnue": 1}},
                               "lighthouse": {"performance": 50, "accessibilite": 80, "bonnes_pratiques": 70, "seo": 85, "lcp_s": 4.0, "tbt_ms": 500, "cls": 0.3},
                               "ecoindex": {"note": "E", "score": 30, "dom": 2000, "requetes": 150, "poids_ko": 4000, "ges_g": 2.5, "eau_cl": 3.7}},
             "https://a.fr/cart": {"gabarit": "Panier", "lighthouse": {"erreur": "délai dépassé"},
                                   "ibm": {"violations": 2, "regles": 1, "par_regle": {"img_alt_valid": 1}}},
             "https://a.fr/p": {"gabarit": "Produit", "lighthouse": {"performance": 95, "accessibilite": 95, "bonnes_pratiques": 95, "seo": 95,
                                                                     "lcp_s": 1.0, "tbt_ms": 10, "cls": 0.0},
                                "ecoindex": {"note": "A", "score": 85, "dom": 300, "requetes": 20, "poids_ko": 500, "ges_g": 1.1, "eau_cl": 1.6}},
             "https://a.fr/s": {"gabarit": "Recherche"},
             "https://a.fr/x": {"gabarit": "Compte", "non_teste": "hors du site"}}
    ecrire_json(r / "resultats/outils-2026-11-12/pages.json", {"Boutique A": {"pages": pages, "traceurs": {
        "cookies_avant_consentement": 4, "cookies_de_mesure": ["_ga"], "traceurs_connus": ["google-analytics.com"], "bandeau_consentement": True}}})
    ecrire_json(r / "resultats/outils-2026-11-12/en_ligne.json", {"Boutique A": {
        "ssllabs": {"notes": ["A", "A+"], "serveurs": 2, "details_url": "https://ssllabs/x"},
        "observatory": {"grade": "B", "score": 70, "score_corrige": 85, "details_url": "https://obs/x", "tests_passed": 8, "tests_failed": 2,
                        "tests_quantity": 10, "penalites": [["a", "hsts-implemented-max-age-less-than-six-months", -10], ["b", "inconnu", 5]]},
        "nu": {"https://a.fr/": {"gabarit": "Accueil", "erreurs": 3, "avertissements": 1, "details_url": "https://nu/x",
                                  "principales": [["Duplicate ID x", 2], ["Message inconnu", 1]]},
               "https://a.fr/p": {"gabarit": "Produit", "erreurs": 0, "avertissements": 0, "details_url": "https://nu/p", "principales": []},
               "https://a.fr/cart": {"gabarit": "Panier", "erreur": "page non lue"}}}})
    ecrire_json(r / "resultats/parcours-2026-11-12/parcours.json", {
        "Boutique A": {"erreur": "délai", "clavier_accueil": {"elements_atteints": 20, "tabulations": 30, "sans_indicateur": 2},
                       "clavier_produit": {"bouton_panier_atteint_en_tabulations": 12, "ajout_au_clavier": False},
                       "formulaire": {"trouve": True, "valide": False, "message_navigateur": "Adresse invalide"},
                       "paiement": {"connexion_obligatoire": False, "moyens_paiement": ["CB", "PayPal"], "etapes": [],
                                    "cases_precochees": ["Recevoir nos offres par e-mail"]}},
        "Boutique Y": {"paiement": {"cases_precochees": ["Adresse de facturation"], "non_teste": "bloqué"}},
        "Boutique Z": {"paiement": {"cases_precochees": []}},
        "Boutique F": {"paiement": {}}})
    ecrire_json(r / "referentiel/exclusions-sites.json", {"Boutique A": [17], "_raison": "Retirée pour ce site", "_raisons": {"17": "Sans objet ici"}})
    with (r / "referentiel/repartition-regles.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["numero", "theme", "regle", "methode", "outil", "raison"])
        for n in range(1, 246):
            m, raison = ("manuel", "") if n in (5, 18) else ("écartée", "Retirée le 12/11 : non testable") if n == 8 else \
                ("écartée", "Écartée pour l'instant") if n in (3, 9) else ("réseau", "")
            w.writerow([n, "t", "r", m, "o", raison])
    (r / "referentiel/recommandations.csv").write_text(
        "code,niveau,recommandation\n2,thème,Reco 2\n4,thème,Reco 4\n16,thème,Reco 16\n19,thème,Reco 19\n33,thème,Reco 33\n166,thème,R166\n80,thème,R80\n87,thème,R87\n",
        encoding="utf-8")


def test_main_complet(gs, capsys):
    preparer(gs)
    g.main()
    html = (gs / "suivi-barometre.html").read_text(encoding="utf-8")
    assert html.startswith("<html><head><style>body{} ") and ".ancien" not in html and "/* Onglets */" in html
    assert "—" not in html and 'id="boutique-a"' in html and 'id="klaviyo-boutique-f"' in html
    for morceau in ("Baromètre des sites", "Lecture critique : faux positifs", "Contre-examen manuel et parcours réels",
                    "Recoupement par les outils", "Fusion de la branche", "Les 4 critères de la checklist e-mail",
                    "Lecture critique : recoupement par axe-core et checkdmarc", "à arbitrer par Mattea", "Sans objet ici"):
        assert morceau in html, morceau
    etat = g.ETAT["sites"]["Boutique A"]
    assert "8" not in etat and "17" not in etat and "3" in etat
    assert etat["5"]["statut"] == "C" and etat["5"]["determinant"][0].startswith("Contre-examen (tranché")
    assert etat["18"]["determinant"][0] == "Contre-examen : parcours de Mattea"
    assert etat["4"]["statut"] == "NC" and etat["4"]["recommandation"] == "Sur Boutique A : Reco 4" and "6" in etat
    assert etat["19"]["statut"] == "NC" and etat["19"]["recommandation"] == "Sur Boutique A : Reco 19"
    assert etat["2"]["statut"] == "C" and etat["2"]["recommandation"] == ""
    assert etat["16"]["statut"] == "NC" and "Une seule source" in etat["16"]["determinant"][0]
    assert etat["17" if "17" in etat else "1"]
    assert etat["33"]["statut"] == "NC" and etat["33"]["sources"]
    assert g.ETAT["sites"]["Boutique Y"]["33"]["statut"] == "C" and g.ETAT["sites"]["Boutique Y"]["33"]["sources"] == []
    assert g.ETAT["sites"]["Boutique Y"]["1"]["statut"] == "NC" and etat["20"]["statut"] == "C"
    em = g.ETAT["emails"]["Klaviyo Boutique C"]
    assert em["EM02"]["ecrans"]["BOUTIQUEC-EM-FOOTER"][0] == "NC" and em["EM10"]["ecrans"]["BOUTIQUEC-EM-POPUP"][0] == "C"
    assert em["EM35"]["ecrans"]["BOUTIQUEC-EM-FOOTER"][0] == "I" and em["EM10"]["statut"] == "C"
    scores = list(csv.reader((gs / "resultats" / f"scores-{date.today():%Y-%m-%d}" / "scores.csv").open(encoding="utf-8")))
    assert scores[0] == ["service", "audit", "score_sur_100", "note"] and any(x[1] == "checklist" for x in scores)
    assert "onglets de service" in capsys.readouterr().out


def test_vue_ensemble_sans_donnees(gs):
    h = g.vue_ensemble({}, {})
    assert "contrôles en cours" in h and "0 critère évalué" in h and "Fusion de la branche" in h


# --- fonctions isolées ------------------------------------------------------

def test_pastille_et_bloc_reseau():
    assert g.pastille("inconnu") == '<span class="pill p-na">inconnu</span>'
    d = {"site": [{"rule_number": 198, "status": "conforme", "comment": "ok"}],
         "pages": [{"gabarit": "Accueil (avec formulaire newsletter)", "statut_http": 200,
                    "poids": {"html_transfere_octets": 2048, "html_decompresse_octets": 4096, "scripts": 1, "styles": 2, "images": 3, "tiers_sans_integrity": 0},
                    "controles": [{"rule_number": 199, "status": "non-conforme", "comment": "c"}, {"rule_number": 200, "status": "bizarre", "comment": "?"}]},
                   {"gabarit": "Panier", "statut_http": 429, "poids": {}, "controles": [{"rule_number": 200, "status": "non-testé", "comment": "429"}]}]}
    h = g.bloc_reseau(d)
    assert "<th>Accueil</th>" in h and "2 Ko" in h and "<td>-</td>" in h and "·" in h and "?" in h and "non testé" in h


def test_bloc_axe():
    a = {"pages_testees": 3, "pages_non_testees": 0, "regles": {
        "image-alt": {"gravite": "critical", "criteres": ["1.1.1"], "pages": 1, "elements": 1},
        "autre": {"gravite": "bizarre", "criteres": [], "pages": 3, "elements": 4}}}
    h = g.bloc_axe(a)
    assert "hors périmètre" not in h and "critique" in h and "bizarre" in h
    assert "1 hors périmètre" in g.bloc_axe(dict(a, pages_non_testees=1))


def test_blocs_etat(gs):
    g.ETAT.update({"sites": {"Boutique A": {"1": regle("NC", pages_nc=["Accueil"]), "2": regle("C"), "3": regle("NA"), "4": regle("NT")}},
                   "emails": {"Klaviyo Boutique C": {
                       "EM02": {"titre": "A", "theme": "t", "statut": "NC", "recommandation": "", "source": {"nom": "n", "url": "u"},
                                "ecrans": {"BOUTIQUEC-EM-POPUP": ["NC", "x"]}},
                       "EM03": {"titre": "B", "theme": "t", "statut": "I", "recommandation": "", "source": {"nom": "n", "url": "u"},
                                "ecrans": {"BOUTIQUEC-EM-POPUP": ["C", "x"]}}}}})
    assert g.bloc_etat_site({"nom": "Boutique Z", "id": "z"}) == ""
    h = g.bloc_etat_site({"nom": "Boutique A", "id": "a"})
    assert "Pages non conformes : Accueil" in h and "50 %" in h
    g.ETAT["sites"]["Boutique B"] = {"1": regle("NA")}
    assert "Taux de conformité : <strong>-</strong>" in g.bloc_etat_site({"nom": "Boutique B", "id": "b"})
    assert g.bloc_etat_email({"nom": "Klaviyo Boutique F", "id": "f"}) == ""
    h = g.bloc_etat_email({"nom": "Klaviyo Boutique C", "id": "c"})
    assert 'data-statut="NT"' in h and "Popup : x" in h


def test_indicateurs_de_navigation(gs):
    assert g.TAUX_NAV("Boutique A") == "à faire" and g.RESUME_SITES() == "contrôles en cours" and g.RESUME_MAILS().startswith("0 critère")
    assert "à faire" in g.TAUX_SITE("Boutique A") and "0 sur 41" in g.CRIT_COMPTE("Klaviyo Boutique C", 41)
    assert "à vérifier" in g.SOMBRE_COMPTE("x") and "à évaluer" in g.THEME_COMPTE("x", "t")
    g.ETAT.update({"sites": {"Boutique A": {"1": regle("C"), "2": regle("NC")}, "Boutique B": {"1": regle("NA")}},
                   "emails": {"Klaviyo Boutique C": {"EM35": {"statut": "NC", "theme": "Mode sombre"}, "EM01": {"statut": "C", "theme": "A"}}}})
    assert g.TAUX_NAV("Boutique A") == "50 %" and g.TAUX_NAV("Boutique B") == "à faire"
    assert g.RESUME_SITES() == "2 sites mesurés : 0 à 50 % de conformité"
    assert "50 % conformes, 1 règles non conformes" in g.TAUX_SITE("Boutique A")
    assert "non prévu" in g.SOMBRE_COMPTE("Klaviyo Boutique C")
    g.ETAT["emails"]["Klaviyo Boutique C"]["EM35"]["statut"] = "C"
    assert "prévu" in g.SOMBRE_COMPTE("Klaviyo Boutique C")
    assert "conformes, aucun non conforme" in g.THEME_COMPTE("Klaviyo Boutique C", "A")
    g.ETAT["emails"]["Klaviyo Boutique C"]["EM01"]["statut"] = "NC"
    assert "1 non conforme(s) sur 1" in g.THEME_COMPTE("Klaviyo Boutique C", "A")
    assert g.RESUME_MAILS() == "1 compte(s) évalué(s) : 1 à 1 critères non conformes ; 1 à connecter"
    g.ETAT["emails"]["Klaviyo Boutique F"] = {"EM01": {"statut": "C", "theme": "A"}}
    assert g.RESUME_MAILS() == "1 compte(s) évalué(s) : 0 à 1 critères non conformes".replace("1 compte(s)", "2 compte(s)")


def test_exemple_reco_acc_lien(gs):
    g.EXEMPLES["12"] = "<code>"
    assert "Exemple clé en main" in g.exemple(12) and g.exemple(13) == ""
    assert g.reco("", 12) == "" and g.reco("x", 13) == "x"
    assert 'id="i"' in g.acc("t", "r", "c", True, "i") and " open" in g.acc("t", "r", "c", True)
    assert 'class="ancre"' in g.lien("a", "#x") and 'target="_blank"' in g.lien("a", "https://x")


def test_composants(gs, monkeypatch):
    monkeypatch.setattr(g, "AUD", {"base": "https://esm/", "scripts": {"A": "s"}, "basics": {"A": "b"}, "contre_examen": {}})
    assert g.comp_scripts("A", {"1": {"scripts": "C"}, "2": {"scripts": None}})[0] == "1 conformes, 0 non conformes"
    assert g.comp_basics("A", {})[0] == "score -"
    g.COMPLEMENTS["scores_basics"] = {"A": 53.1}
    assert g.comp_basics("A", {}) == ("score 53,1 %", "ok", "https://esm/b") and g.scores_site("A")["opquast-basics"] == 53
    assert g.comp_ce("A", {}) == ("à faire", "afaire", "")
    g.FICHE["A"] = [{"decision_statut": "NC"}, {"decision_statut": None}]
    assert g.comp_ce("A", {})[2] == "" and "1 / 2 tranchées" in g.comp_ce("A", {})[0]
    assert g.comp_axe("A", {})[0] == "à faire" and g.comp_ibm("A", {})[0] == "à faire"
    assert g.comp_lh("A", {})[0] == "en cours" and g.comp_eco("A", {})[0] == "à faire"
    assert g.comp_nu("A", {})[0] == "à faire" and g.comp_obs("A", {})[0] == "à faire"
    assert g.comp_ssl("A", {})[0] == "à faire" and g.comp_trac("A", {})[0] == "à faire"
    g.OUTILS_PAGES["A"] = {"pages": {f"u{i}": {"lighthouse": {"performance": i, "accessibilite": i}} for i in range(4)}}
    assert g.comp_lh("A", {})[1] == "ok"
    g.OUTILS_LIGNE["A"] = {"observatory": {"grade": "B", "score": 70, "details_url": "u"},
                           "nu": {"a": {"erreurs": 1}, "b": {"erreur": "x"}}}
    assert g.comp_obs("A", {})[0] == "note B (70/100)" and g.comp_nu("A", {})[1] == "attention"
    assert g.comp_outil("axe-core")("A", {})[0] == "à faire"
    assert g.score_email("x") == {"checklist": None, "global": None}


def test_scores_et_notes(gs, monkeypatch):
    assert g.note_lettre(None) == "-" and g.note_lettre(91) == "A" and g.note_lettre(10) == "E"
    assert "à faire" in g.pastille_score(None) and "(B)" in g.pastille_score(85) and "attention" not in g.pastille_score(85)
    assert "p-block" in g.pastille_score(20, True) and "(D)" not in g.pastille_score(55, True)
    g.AXE["sites"] = {"A": {"pages": [{"teste": False}]}}
    monkeypatch.setattr(g, "FAMILLES", [("f", "Famille", 50, ["axe", "ibm"]), ("g", "Vide", 50, ["nu"])])
    g.OUTILS_PAGES["A"] = {"pages": {"u": {"ibm": {"regles": 2}}}, "traceurs": {"cookies_de_mesure": ["a", "b"]}}
    sc = g.scores_site("A")
    assert sc["axe"] is None and sc["ibm"] == 90 and sc["traceurs"] == 50 and sc["familles"] == {"f": 90, "g": None}
    g.AUD.update(lire_json(gs / "referentiel/audits-esm.json"))
    sites = g.onglet_barometre_sites({}, {})
    assert "Famille <small>(50 %)</small>" in sites


def test_reco_outils():
    assert g.reco_nu("Bad value x") == ("Valeur d'attribut invalide", g.NU_FR[3][2], "nu")
    assert g.reco_nu("zzz")[0] == "zzz"
    bon = {"lcp_s": 1, "tbt_ms": 10, "cls": 0, "bonnes_pratiques": 95, "accessibilite": 95, "seo": 95}
    assert g.reco_lighthouse(bon) == "Rien de prioritaire."
    assert g.reco_lighthouse({"lcp_s": 3, "tbt_ms": 400, "cls": 0.2, "bonnes_pratiques": 50, "accessibilite": 50, "seo": 50}).count(";") == 5
    assert g.reco_eco({"dom": 10, "requetes": 10, "poids_ko": 10}) == "Rien de prioritaire."
    assert g.reco_eco({"dom": 2000, "requetes": 200, "poids_ko": 4000}).count(";") == 2


def test_graphiques():
    assert g.svg_barres([], 100, "t") == ""
    assert 'width="2.0"' in g.svg_barres([("a", 0, "0")], 0, "t")
    h = g.svg_empile([("a", {"C": 1, "NC": 1}), ("b", {})], "t")
    assert "50 %" in h and "(1)" not in h
    assert "(1)" in g.svg_empile([("a", {"C": 1})], "t")
    assert g.comptes_statuts({"1": {"statut": "I"}})["NT"] == 1 and g.moyenne([]) == 0


def test_blocs_outils(gs):
    preparer(gs)
    g.charger_annexes()
    h = g.bloc_ibm("Boutique A")
    assert "Image sans alternative valide" in h and "inconnue" in h
    h = g.bloc_lighthouse("Boutique A")
    assert "gabarit non mesuré" in h and "délai dépassé" in h and "Non testé : hors du site" in h and "LCP 4.0 s" in h
    assert "Moyenne des gabarits" not in g.bloc_lighthouse("Boutique Z")
    h = g.bloc_ecoindex("Boutique A")
    assert "<strong>E</strong>" in h and "<td>-</td>" in h
    h = g.bloc_nu("Boutique A")
    assert "Identifiants en double" in h and "Aucune erreur." in h and "À refaire" in h
    assert "Score corrigé retenu" in g.bloc_observatory("Boutique A") and g.bloc_observatory("Boutique Z") == ""
    g.OUTILS_LIGNE["Boutique A"]["observatory"] = {"grade": "C", "score": 50, "details_url": "u", "tests_passed": 1, "tests_failed": 1,
                                                   "tests_quantity": 2, "penalites": []}
    h = g.bloc_observatory("Boutique A")
    assert "Score corrigé" not in h and "<table" not in h
    assert "A, A+" in g.bloc_ssl("Boutique A") and g.bloc_ssl("Boutique Z") == ""
    assert "bloquer _ga" in g.bloc_traceurs("Boutique A") and g.bloc_traceurs("Boutique Z") == ""
    g.OUTILS_PAGES["Boutique A"]["traceurs"] = {"cookies_avant_consentement": 0, "cookies_de_mesure": [], "traceurs_connus": []}
    h = g.bloc_traceurs("Boutique A")
    assert "aucun" in h and "non repéré" in h and "vérifier, cookie par cookie" in h


def test_liens_ecart_et_lecture(gs):
    preparer(gs)
    g.charger_annexes()
    x = {"entre": "nos outils entre eux", "base": [["REDbot", "C"], ["Validateur Nu (W3C)", "NC"], ["Inconnu", "C"]]}
    liens = g.liens_ecart(x, "Boutique A", "a")
    assert "Validateur Nu" in liens and "Opquast scripts sans IA" in liens
    g.OUTILS_LIGNE["Boutique A"]["nu"] = {}
    assert "#a-nu" in g.liens_ecart({"entre": "nos outils entre eux", "base": []}, "Boutique A", "a")
    assert g.bloc_lecture("Boutique X", "x") == ("", "à faire")
    assert g.bloc_contre_examen("Boutique X") == ("", "à faire")
    assert g.bloc_parcours("Boutique X") == ""


@pytest.mark.parametrize("parcours, morceau", [
    ({"clavier_produit": {"bouton_panier_atteint_en_tabulations": 5, "ajout_au_clavier": True}}, "ajout au clavier réussi"),
    ({"clavier_produit": {"bouton_panier_atteint_en_tabulations": None, "ajout_au_clavier": False}}, "non atteint en 80 tabulations"),
    ({"formulaire": {"trouve": True, "message_propre_au_site": True}}, "novalidate"),
    ({"formulaire": {"trouve": True, "valide": True}}, "Acceptée sans vérification"),
    ({"formulaire": {"trouve": False}}, "<ul class=\"items\">\n</ul>"),
    ({"paiement": {"connexion_obligatoire": True, "moyens_paiement": [], "etapes": ["Panier", "Paiement"], "cases_precochees": []}}, "Connexion exigée"),
])
def test_bloc_parcours_variantes(gs, parcours, morceau):
    g.PARCOURS_RES["A"] = parcours
    h = g.bloc_parcours("A")
    assert morceau in h
    if "paiement" in parcours:
        assert "Panier &gt; Paiement" in h and "Aucune inscription" in h


def test_bloc_lecture_sans_autres_ecarts(gs, monkeypatch):
    g.AUD.update(lire_json(gs / "referentiel/audits-esm.json"))
    x = {"type": "faux positif", "regle": "1", "titre": "T", "entre": "", "constat": "c", "pourquoi": "p", "recommandation": "",
         "statut": "C", "statut_lib": "conforme", "base": []}
    g.LECTURE["Boutique A"] = {"accords_robot_scripts": 0, "ecarts": [x], "trois_interessants": [x]}
    corps, res = g.bloc_lecture("Boutique A", "a")
    assert "autres écarts" not in corps and res == "1 faux positif(s), 0 faux négatif(s), 1 écarts"


def test_bloc_recoupement_sans_sources(gs):
    g.LECTURE["A"] = {"recoupement": {"1": {"axe-core": "C"}, "x": {"curl": "NC"}}, "sources_par_regle": {}}
    h = g.bloc_recoupement("A", "a", {"1": {"statut": "ZZ"}}, {1: {"description": {"fr": "Règle un"}}})
    assert "Règle un" in h and "une seule source" in h


def test_onglet_compte_email_variantes(gs, monkeypatch):
    s = next(x for x in g.SERVICES if x["nom"] == "Klaviyo Boutique F")
    h = g.onglet_compte_email(s)
    assert "Accès au compte e-mail" in h and "Pas encore évalué." in h and "MAJ-EM-POPUP" not in h and "<th>Pied de page</th>" in h
    g.ETAT["emails"] = {"Klaviyo Boutique F": {"EM02": {"titre": "A", "theme": "t", "statut": "NA", "recommandation": "",
                                                        "ecrans": {"BOUTIQUEC-EM-POPUP": ["C", "x"]}, "source": {"nom": "n", "url": "u"}}}}
    g.ETAT["emails"]["Klaviyo Boutique F"]["EM10"] = {"titre": "B", "theme": "t", "statut": "C", "recommandation": "",
                                                       "ecrans": {}, "source": {"nom": "n", "url": "u"}}
    g.LECTURE["_emails"] = {"Klaviyo Boutique F": {"ecarts": [], "recoupement": {}}}
    h = g.onglet_compte_email(s)
    assert "Lecture critique : recoupement" not in h and "100<small>" in h


def test_bilan_et_remplir_tests():
    v = {"site": [{"rule_number": 1, "status": "conforme"}],
         "pages": [{"gabarit": "A", "statut_http": 200, "controles": [
             {"rule_number": 2, "status": "non-testé"}, {"rule_number": 2, "status": "conforme"},
             {"rule_number": 3, "status": "non-conforme"}, {"rule_number": 3, "status": "conforme"},
             {"rule_number": 4, "status": "non-applicable"}, {"rule_number": 4, "status": "conforme"},
             {"rule_number": 1, "status": "conforme"}]},
                   {"gabarit": "B", "statut_http": 429, "controles": []}]}
    b = g.bilan(v)
    assert b == {"conformes": 3, "nc": [3], "non_testees": ["B"]}
    s = {"nom": "A", "reseau": "A", "tests": [("1", "t", "o", "RESEAU", "RESEAU"), ("2", "t", "o", "ok", "x")]}
    g.remplir_tests(s, {"A": {"site": [{"rule_number": 1, "status": "conforme"}], "pages": []}}, {"sites": {"A": {
        "pages_testees": 1, "regles_en_violation": 0, "regles_critiques": 0, "elements_en_defaut": 0}}})
    assert s["tests"][0][3:] == ("ok", "1 conformes, 0 non conformes (aucune)") and s["tests"][2][3] == "ok"
    s = {"nom": "B", "reseau": "B", "tests": [("1", "t", "o", "RESEAU", "RESEAU")]}
    g.remplir_tests(s, {}, None)
    assert s["tests"][0][3:] == ("afaire", "Passage en cours")


def test_git_log(monkeypatch):
    monkeypatch.setattr(__import__("subprocess"), "run", lambda *a, **k: SimpleNamespace(stdout="abc|12/11|Fusion|x\nmauvaise ligne\n"))
    assert g.git_log() == [("abc", "12/11", "Fusion|x")]


def test_liens_locaux(tmp_path):
    assert g.liens_locaux(tmp_path / "absent.json") == []
    f = ecrire_json(tmp_path / "l.json", [{"titre": "Suivi", "url": "https://x"}, {"titre": "B", "url": "u", "detail": "d"}])
    assert g.liens_locaux(f) == [("Suivi", "https://x", ""), ("B", "u", "d")]


def test_charger_sans_fichiers(gs):
    assert g.charger_axe() == {} and g.charger_etat() == {} and g.dernier_json("resultats/rien-*") == {}
    assert g.charger_reseau() == ({}, {}) and g.onglet_etat() == ""


# --- exporter_csv -----------------------------------------------------------

def test_par_groupe_et_note():
    assert ex.par_groupe({"axe-core": "C", "axe-core et IBM (aria-hidden, tableaux)": "NC", "Sa11y": "NA", "Inconnu": "NT", "Autre": "C"}) == {
        "axe": "NC", "Sa11y": "NA", "Autre": "C"}
    assert ex.par_groupe({"Sa11y": "NA", "Siteimprove Alfa": "C"}) == {"Sa11y": "NA", "Alfa": "C"}
    assert [ex.note(x) for x in (None, 95, 85, 70, 55, 10)] == ["-", "A", "B", "C", "D", "E"]


def test_exporter_csv(gs, capsys):
    preparer(gs)
    g.ETAT["sites"] = {}
    lecture = lire_json(gs / "resultats/lecture-critique-2026-11-12/lecture.json")
    lecture["Boutique A"]["recoupement"]["2"]["Lecture IA indépendante (probabiliste)"] = "NT"
    ecrire_json(gs / "resultats/lecture-critique-2026-11-12/lecture.json", lecture)
    etat = lire_json(gs / "resultats/etat-2026-11-12/etat.json")
    etat["sites"]["Boutique A"]["999"] = regle("C", titre="Hors référentiel", theme="Divers")
    etat["sites"]["Boutique C"] = {"1": regle("NA")}
    ecrire_json(gs / "resultats/etat-2026-11-12/etat.json", etat)
    assert ex.main() == 0
    d = gs / "resultats" / f"barometre-{date.today():%Y-%m-%d}"
    lignes = list(csv.DictReader((d / "barometre.csv").open(encoding="utf-8-sig"), delimiter=";"))
    a = {l["regle"]: l for l in lignes if l["site"] == "Boutique A"}
    assert a["1"]["nb_sources"] == "2" and a["1"]["audit axe"] == "conforme" and a["1"]["audit Lighthouse"] == "non conforme"
    assert a["19"]["ecart_entre_sources"] == "faux positif" and a["19"]["a_arbitrer"] == "oui" and a["19"]["recommandation"]
    assert a["999"]["theme"] == "Divers" and a["999"]["intitule"] == "Hors référentiel"
    tests = list(csv.DictReader((d / "tests.csv").open(encoding="utf-8-sig"), delimiter=";"))
    t1 = [t for t in tests if t["site"] == "Boutique A" and t["regle"] == "1"]
    assert {t["accord_avec_la_decision"] for t in t1} == {"oui", "non"}
    scores = list(csv.DictReader((d / "scores.csv").open(encoding="utf-8-sig"), delimiter=";"))
    assert {s["site"] for s in scores} == {"Boutique A", "Boutique C", "Boutique Y"} and next(s for s in scores if s["site"] == "Boutique C")["note"] == "-"
    assert "lignes ->" in capsys.readouterr().out


# --- parc et compléments -----------------------------------------------------

def test_construire_services(gs):
    """Onglets tirés du parc et du CSV : sites (écrans, préfixe de langue, site sans écran), puis comptes e-mail."""
    noms = [x["nom"] for x in g.SERVICES]
    assert noms == ["Boutique A", "Boutique C", "Boutique F", "Klaviyo Boutique C", "Klaviyo Boutique F"]
    a, c, f = g.SERVICES[:3]
    assert a["id"] == "boutique-a" and a["ecrans"] == [("Accueil", "/"), ("Recherche", "/search?q=x")] and a["version"] == "Production · https://a.fr/"
    assert c["version"] == "Production · https://c.fr/products/p" and f["ecrans"] == [] and f["version"] == "Production · "
    assert g.SERVICES[3]["cat"] == "CRM" and g.SERVICES[3]["ecrans"][0] == ("Popup", "BOUTIQUEC-EM-POPUP")
    ecrire_json(gs / "referentiel/parc.json", {"sites": [dict(PARC_ORIGINE["sites"][3], nom="Été à Noël", plateforme="")]})
    s = g.construire_services()[0]
    assert s["id"] == "ete-a-noel" and "plateforme shopify, version auditée sous /fr" in s["desc"]
    assert g.ident("!!!") == "service"


def test_ecrans_email(gs):
    assert [c for c, _ in g.ecrans_email("Klaviyo Boutique F")][:2] == ["MAJ-EM-POPUP", "MAJ-EM-FOOTER"]
    assert g.ecrans_email("Inconnu")[0] == ("POPUP", "Popup")
    g.ETAT["emails"] = {"Klaviyo Boutique C": {"EM01": {"ecrans": {"BOUTIQUEC-EM-ZZZ": ["C", ""], "BOUTIQUEC-EM-FOOTER": ["C", ""]}},
                                               "EM02": {"ecrans": {"BOUTIQUEC-EM-POPUP": ["C", ""]}}}}
    assert g.ecrans_email("Klaviyo Boutique C") == [("BOUTIQUEC-EM-POPUP", "Popup"), ("BOUTIQUEC-EM-FOOTER", "Pied de page"), ("BOUTIQUEC-EM-ZZZ", "Zzz")]


def test_main_avec_complements(gs, capsys):
    """Compléments optionnels : tests et descriptions par service, Fait / À faire, liens, jalons, pied, scores basics."""
    preparer(gs)
    ecrire_json(gs / "referentiel/suivi-complements.json", {
        "services": {"Boutique A": {"desc": "Confitures", "tests": [["05/11", "Type de site", "navigateur", "ok", "Shopify"]]}},
        "fait": [["Cadrage", [["Parc arrêté", "8 services"]]]], "a_faire": [["Ensuite", [["Relire", "les écarts"]]]],
        "liens": [["Dépôt", "https://exemple.org/depot", "privé"]], "jalons": [["ok", "J1 · cadrage"], ["", "J3 · baromètre"]],
        "pied": "Liens privés.", "scores_basics": {"Boutique A": 53.1}})
    g.main()
    html = (gs / "suivi-barometre.html").read_text(encoding="utf-8")
    assert "Parc arrêté" in html and "Relire" in html and "https://exemple.org/depot" in html and "Liens privés." in html
    assert '<li class="ok">J1 · cadrage</li>' in html and "<li>J3 · baromètre</li>" in html and "score 53,1 %" in html
    assert next(x for x in g.SERVICES if x["nom"] == "Boutique A")["tests"][0][0] == "05/11"
    assert "Rien de consigné" not in html


def test_main_sans_complements(gs):
    """Sans compléments : listes vides signalées, pas de jalons, aucun nom de la mission d'origine."""
    preparer(gs)
    g.main()
    html = (gs / "suivi-barometre.html").read_text(encoding="utf-8")
    assert html.count("Rien de consigné") == 2 and "milestones" not in html.split("</style>")[-1]
    for mot in ("itsmatlsr", "Secrets de", "J2 · 12 nov", "Klaviyo installé"):  # Colorz reste dans referentiel/audits-esm.json (hors de ce script)
        assert mot not in html, mot
    a = next(x for x in g.SERVICES if x["nom"] == "Boutique A")
    assert a["tests"][0][:2] == ("2026-11-12", "Contrôles réseau")
