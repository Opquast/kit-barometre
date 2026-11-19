"""Tests des scripts du matin : bilan_journal.py, ecarts_a_trancher.py, compte_rendu.py."""

from __future__ import annotations

import json
import os
import sys

import pytest

import barometre as bm
import bilan_journal as bj
import compte_rendu as cr
import ecarts_a_trancher as ea
from conftest import ecrire_json


def ecrire(chemin, texte):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(texte, encoding="utf-8")
    return chemin


def etat(**kw):
    base = {"date": "2026-11-19", "termine": True, "code": 0, "hors": "/h", "echecs": [], "reprise": None,
            "etapes": {"mesure": {"statut": "fait", "commandes": [{"nom": "a.py", "commande": "python a.py", "code": 0, "duree_s": 1}]},
                       "synthese": {"statut": "fait", "commandes": []}}}
    base.update(kw)
    return base


# --- bilan_journal -----------------------------------------------------------

def test_bilan_rien_a_lire(racine, capsys):
    racine(bj)
    assert bj.main([]) == 2
    assert "Rien à lire" in capsys.readouterr().err


def test_bilan_etat_ok(racine, capsys):
    r = racine(bj)
    ecrire_json(r / "resultats/etat-passage-2026-11-19.json", etat())
    ecrire(r / "resultats/journal-barometre-2026-11-18.log", "vieux")
    assert bj.main([]) == 0
    out = capsys.readouterr().out
    assert "etat-passage-2026-11-19.json" in out and "fait      mesure (1 commande(s))" in out and "Échecs : 0" in out and "Reprise" not in out


def test_bilan_etat_echec(racine, capsys):
    r = racine(bj)
    f = ecrire_json(r / "x.json", etat(code=1, echecs=[{"etape": "mesure", "commande": "node p.mjs", "code": 3}],
                                       reprise="python3 scripts/barometre.py --hors /h --depuis mesure"))
    assert bj.main(["--etat", str(f)]) == 1
    out = capsys.readouterr().out
    assert "mesure : node p.mjs (code 3)" in out and "Reprise : python3 scripts/barometre.py --hors /h --depuis mesure" in out


@pytest.mark.parametrize("etapes, attendu", [
    ({"mesure": {"statut": "fait", "commandes": []}, "releve": {"statut": "en cours", "commandes": []}}, "--depuis releve"),
    ({"mesure": {"statut": "fait", "commandes": []}, "releve": {"statut": "à faire", "commandes": []}}, "--depuis releve"),
    ({"mesure": {"statut": "fait", "commandes": []}}, None),
])
def test_bilan_etat_non_termine(racine, capsys, etapes, attendu):
    r = racine(bj)
    f = ecrire_json(r / "x.json", etat(termine=False, etapes=etapes))
    assert bj.main(["--etat", str(f)]) == 3
    out = capsys.readouterr().out
    assert "Passage non terminé" in out
    assert (attendu in out) if attendu else ("Reprise" not in out)


def test_bilan_journal_plus_recent_renvoie_a_l_etat(racine, capsys):
    r = racine(bj)
    ecrire_json(r / "resultats/etat-passage-2026-11-18.json", etat(date="2026-11-18"))
    e = ecrire_json(r / "resultats/etat-passage-2026-11-20.json.bak", {})  # ignoré : autre motif
    assert e.exists()
    vrai = ecrire_json(r / "resultats/autre.json", etat(code=1, echecs=[{"etape": "sources", "commande": "c", "code": 2}], reprise="R"))
    ecrire(r / "resultats/journal-barometre-2026-11-19.log",
           f"\n===== début 2026-11-19 22:00:00 : vieux\n=== mesure\n\n===== début 2026-11-19 23:00:00 : x\nÉtat du passage : {vrai}\n===== fin\n")
    assert bj.main([]) == 1
    assert "Reprise : R" in capsys.readouterr().out


JOURNAL_ANCIEN = """
===== début 2026-11-19 22:00:00 : caffeinate -dimsu /usr/bin/python3 /k/scripts/barometre.py --hors '/t/h h' --depuis mesure --continuer --service X
=== mesure
  $ python3 scripts/controles_reseau.py --service X
  $ node scripts/page_playwright.mjs --service X
beaucoup de lignes
=== releve
  $ node scripts/releve_regles.mjs /t/textes
=== sources
Bilan :
  ok  mesure      controles_reseau.py        10 s
  ÉCHEC mesure      page_playwright.mjs        3 s
  ok  releve      releve_regles.mjs          4 s
===== fin 2026-11-20 05:00:00, code 0
"""


def test_bilan_journal_ancien_format(racine, capsys):
    r = racine(bj)
    ecrire(r / "resultats/journal-barometre-2026-11-19.log", JOURNAL_ANCIEN)
    assert bj.main([]) == 1
    out = capsys.readouterr().out
    assert "mesure : node scripts/page_playwright.mjs --service X" in out
    assert "fait      releve" in out and "échec     mesure" in out and "fait      sources" in out
    assert "Reprise : python3 scripts/barometre.py --hors '/t/h h' --service X --depuis mesure" in out


def test_bilan_journal_arret_et_non_termine(racine, capsys):
    r = racine(bj)
    f = ecrire(r / "j.log", "\n===== début 2026-11-19 : python3 barometre.py --hors /h --arreter\n=== synthese\n  $ python3 scripts/fusion_scripts.py\n"
                            "\nÉchec (5) : python3 scripts/fusion_scripts.py. Corriger puis relancer avec --depuis synthese.\n===== fin, code 5\n")
    assert bj.main(["--journal", str(f)]) == 1
    out = capsys.readouterr().out
    assert "synthese : python3 scripts/fusion_scripts.py (code 5)" in out and out.rstrip().endswith("--hors /h --depuis synthese")
    f = ecrire(r / "j2.log", "\n===== début 2026-11-19 : python3 scripts/barometre.py --hors /h\n=== mesure\n=== releve\n  $ node r.mjs\n")
    assert bj.main(["--journal", str(f)]) == 3
    out = capsys.readouterr().out
    assert "commencée releve" in out and "barometre.py --hors /h --depuis releve" in out
    f = ecrire(r / "j3.log", "\n===== début 2026-11-19 : python3 scripts/barometre.py --hors /h\n=== releve\n===== fin\n")
    assert bj.main(["--journal", str(f)]) == 0


def test_bilan_journal_illisible(racine, capsys):
    r = racine(bj)
    ecrire(r / "resultats/journal-barometre-2026-11-19.log", "\n===== début : rien\nAucune étape\n")
    assert bj.main([]) == 2
    assert bj.date_de(None) == "" and bj.date_de(r / "sans-date.log") == ""


def test_bilan_apres_un_vrai_passage(racine, monkeypatch, tmp_path, capsys):
    """barometre.py écrit l'état, bilan_journal.py le relit."""
    r = racine(bm, bj)
    codes = {"fusion_scripts.py": 4}
    monkeypatch.setattr(bm.subprocess, "run", lambda cmd, **kw: type("R", (), {"returncode": codes.get(os.path.basename(cmd[1]), 0)})())
    monkeypatch.setattr(sys, "argv", ["bm", "--hors", str(tmp_path / "hors"), "--depuis", "synthese", "--continuer"])
    assert bm.main() == 1
    capsys.readouterr()
    assert bj.main([]) == 1
    out = capsys.readouterr().out
    assert "fusion_scripts.py" in out and f"--hors {tmp_path / 'hors'} --depuis synthese" in out
    assert (r / "resultats").exists()


# --- ecarts_a_trancher -------------------------------------------------------

def lecture_exemple():
    return {
        "_emails": {"x": {"ecarts": [{"regle": "EM01", "statut": ""}]}},
        "Ma boutique": {
            "recoupement": {"153": {"axe-core": "NC", "Relevé navigateur (Claude)": "C"}},
            "ecarts": [
                {"type": "écart", "regle": "153", "titre": "Fenêtre", "constat": "Non conforme selon axe ; " + "x" * 500,
                 "pourquoi": "Les sources se contredisent.", "recommandation": "Vérifier.", "statut": "NT"},
                {"type": "faux négatif", "regle": "12", "titre": "Titre", "constat": "c", "pourquoi": "p", "recommandation": "r",
                 "statut": "NC", "a_arbitrer": True, "base": [["Robot", "NC"], ["Script", "C"]]},
                {"type": "faux positif", "regle": "13", "titre": "T13", "statut": "C", "base": []},
                {"type": "limite d'outil", "regle": "-", "titre": "Mention", "statut": ""},
            ]},
        "Autre": {"ecarts": [{"type": "écart", "regle": "8", "titre": "Huit", "statut": "", "base": []}]},
    }


def test_ecarts_sans_lecture(racine, capsys):
    racine(ea)
    assert ea.main([]) == 2
    assert "Aucune lecture critique" in capsys.readouterr().err


def test_ecarts_liste(racine, capsys):
    r = racine(ea)
    ecrire_json(r / "resultats/lecture-critique-2026-11-18/lecture.json", {})
    ecrire_json(r / "resultats/lecture-critique-2026-11-19/lecture.json", lecture_exemple())
    assert ea.main([]) == 1
    out = capsys.readouterr().out
    assert "lecture-critique-2026-11-19" in out and "Écarts sans décision : 2" in out
    assert "Ma boutique, règle 153 (écart) : Fenêtre" in out and "Autre, règle 8" in out
    assert "à arbitrer par la personne responsable du baromètre : 1" in out and "règle 12 (retenu : non conforme)" in out
    assert "fiches : --dossier." in out and "EM01" not in out and "Mention" not in out


def test_ecarts_dossier_et_site(racine, tmp_path, capsys):
    racine(ea)
    f = ecrire_json(tmp_path.parent / f"{tmp_path.name}-ext" / "lecture.json", lecture_exemple())
    assert ea.main(["--dossier", "--site", "Ma boutique", "--lecture", str(f)]) == 1
    out = capsys.readouterr().out
    assert "1 écart(s) sans décision, 1 à arbitrer" in out
    assert "[1/2] Ma boutique, règle 153 : Fenêtre" in out and "statut provisoire : non testé" in out
    assert "Sources et verdicts : Relevé navigateur (Claude) = conforme | axe-core = non conforme" in out
    assert "…" in out and 'ANALYSE_SOURCES[("Ma boutique", "153")]' in out
    assert "[2/2] Ma boutique, règle 12" in out and "statut retenu : non conforme ; à arbitrer" in out and "Robot = non conforme" in out
    assert out.rstrip().endswith("relancer --etapes synthese.")


def test_ecarts_aucun_sans_decision(racine, capsys):
    r = racine(ea)
    lc = lecture_exemple()
    del lc["Autre"]
    lc["Ma boutique"]["ecarts"] = lc["Ma boutique"]["ecarts"][1:]
    ecrire_json(r / "resultats/lecture-critique-2026-11-19/lecture.json", lc)
    assert ea.main(["--dossier"]) == 0
    out = capsys.readouterr().out
    assert "0 écart(s) sans décision" in out and "Sources et verdicts : Robot" in out and "Trancher" not in out
    assert "Sources et verdicts : aucune" in ea.fiche(1, 1, "S", {"regle": "1", "statut": ""}, {}, True)


# --- compte_rendu ------------------------------------------------------------

ENTETE_SCORES = "site;score;note;conformes;non_conformes;non_applicables;non_testees;regles_mesurees;part_deux_sources_ou_plus"


def passage(r, scores=None, detail=True, changements=None, jour="2026-11-19"):
    d = r / f"resultats/barometre-{jour}"
    ecrire(d / "scores.csv", "﻿" + (scores or ENTETE_SCORES + "\nMa boutique;66;C;108;55;38;1;202;87 %\nAutre;;-;0;0;0;2;2;0 %\n"))
    if detail:
        ecrire(d / "barometre.csv", "﻿site;regle;statut_retenu;nb_sources;decision_et_raison;determinant\n"
                                    "Ma boutique;1;conforme;2;;\nMa boutique;5;non testé;1;Pas de source;\nAutre;7;non testé;0;;\nAutre;8;non testé;x;;Indice\n")
    if changements is not None:
        ecrire(d / "changements.csv", "﻿date;date_precedente;site;regle;intitule;avant;apres;sens\n" + changements)
    return d


def lancer_cr(r, capsys, *args):
    code = cr.main(list(args))
    return code, capsys.readouterr().out, (r / "resultats").glob("barometre-*/compte-rendu.md")


def test_compte_rendu_sans_scores(racine, capsys):
    racine(cr, ea)
    assert cr.main([]) == 2
    assert "Aucun scores.csv" in capsys.readouterr().err


def test_compte_rendu_complet(racine, capsys):
    r = racine(cr, ea)
    d = passage(r, changements="2026-11-19;2026-11-12;Ma boutique;12;Douze;conforme;non conforme;régression\n"
                               "2026-11-19;2026-11-12;Ma boutique;13;Treize;non conforme;conforme;amélioration\n"
                               "2026-11-19;2026-11-12;Ma boutique;14;Quatorze;absente;conforme;autre\n")
    ecrire_json(r / "resultats/etat-passage-2026-11-19.json", etat(
        etapes={"mesure": {"statut": "fait", "commandes": []}, "releve": {"statut": "fait", "commandes": []},
                "sources": {"statut": "fait", "commandes": []}, "synthese": {"statut": "fait", "commandes": []}}))
    ecrire_json(r / "resultats/etat-passage-2026-12-01.json", {})  # après la date du compte rendu : ignoré
    for n in ("lecture_ia_lot1", "lecture_visuelle_lot1", "lecture_dom_lot1"):
        ecrire_json(r / f"resultats/sources-2026-11-20/{n}.json", {})
    ecrire_json(r / "resultats/sources-2026-11-01/lecture_dom_lot2.json", {})  # passage précédent : ignoré
    lc = lecture_exemple()
    ecrire_json(r / "resultats/lecture-critique-2026-11-20/lecture.json", lc)
    (r / "resultats/esm-basics-2026-11-19").mkdir()
    code, out, _ = lancer_cr(r, capsys)
    assert code == 0 and "Trancher les 2 écart(s) sans décision" in out
    md = (d / "compte-rendu.md").read_text(encoding="utf-8")
    assert "| Ma boutique | 66 | C | 108 | 55 | 38 | 1 | 202 |" in md and "| Autre | - | - |" in md
    assert "- Ma boutique : 87 %" in md and "Ensemble du parc : 25 % (1 statuts sur 4)" in md
    assert "Écarts tranchés : 2 (Ma boutique 2)." in md and "à arbitrer par la personne responsable du baromètre : 1." in md
    assert "règle 12 (non conforme retenu)" in md and "Écarts sans décision : 2. Voir" in md
    assert "règle 5 : Pas de source" in md and "règle 7 : aucune source n'a tranché" in md and "règle 8 : Indice" in md
    assert "eServices Manager" not in md and "non rendue" not in md
    assert "## Ce qui a changé" in md and "3 (1 amélioration(s), 1 régression(s), 1 autre(s))" in md
    assert "De conforme à non conforme :\n- Ma boutique, règle 12 : Douze" in md and "De non conforme à conforme :\n- Ma boutique, règle 13" in md
    assert "Étapes faites : mesure, releve, sources, synthese." in md and "Lecture 3 (DOM, captures et paiement) : rendue (1 fichier(s))" in md
    assert "Synthèse : à jour des lectures" in md and "Étapes non lancées" not in md


def test_compte_rendu_scores_precedents_sans_changement(racine, capsys):
    r = racine(cr, ea)
    d = passage(r, scores=ENTETE_SCORES + ";score_precedent;note_precedente;ecart\nMa boutique;66;C;1;1;1;0;3;50 %;63;D;+3\nAutre;70;C;1;0;0;0;1;0 %;;;\n",
                detail=False, changements="")
    ecrire(d / "changements.csv", "\ufeffsite;regle;intitule;sens\nAutre;3;Trois;régression\n")
    code, out, _ = lancer_cr(r, capsys, "--date", "2026-11-19")
    md = (d / "compte-rendu.md").read_text(encoding="utf-8")
    assert "| Ma boutique | 63 (D) | 66 (C) | +3 |" in md and "| Autre | - (-) | 70 (C) | - |" in md
    assert "1 (0 amélioration(s), 1 régression(s), 0 autre(s))" in md and "De non conforme à conforme" not in md and "Ensemble du parc" not in md
    assert "Détail par règle absent" in md and "aucun export" in md and "Lecture 1 (textes légaux) non rendue." in md
    assert "Aucune lecture critique trouvée" in md and "Aucun état de passage" in md and "Synthèse : antérieure" in md
    assert "Lancer les lectures IA 1" in out


def test_compte_rendu_rien_qui_change(racine, capsys):
    r = racine(cr, ea)
    d = passage(r, detail=False)
    ecrire(d / "barometre.csv", "﻿site;regle;statut_retenu;nb_sources\nMa boutique;1;conforme;2\n")
    lancer_cr(r, capsys)
    md = (d / "compte-rendu.md").read_text(encoding="utf-8")
    assert "## Ce qui a changé" not in md and "Aucune règle mesurée n'est restée non testée." in md
    assert cr.section_changements([], []) == [] and cr.date_de(r / "x") == ""
    assert "Aucune règle n'a changé" in "\n".join(cr.section_changements([{"site": "A", "score": "1", "note": "E", "score_precedent": ""}], []))


@pytest.mark.parametrize("etat_, lectures, a_jour, sans, arb, attendu", [
    ({"echecs": [{"etape": "x"}], "reprise": "REPRISE"}, {}, True, 0, 0, "REPRISE"),
    ({"termine": False, "echecs": []}, {}, True, 0, 0, "Attendre la fin"),
    ({}, {"1": [1], "2": [], "3": []}, True, 0, 0, "lectures IA 1"),
    ({"termine": True}, {"1": [1], "2": [1], "3": []}, False, 0, 0, "plus récentes que la synthèse"),
    ({}, {"1": [1], "2": [1], "3": []}, True, 0, 0, "Lancer la lecture 3"),
    ({}, {"1": [1], "2": [1], "3": [1]}, True, 2, 0, "Trancher les 2"),
    ({}, {"1": [1], "2": [1], "3": [1]}, True, 0, 3, "Présenter à Q les 3"),
    ({}, {"1": [1], "2": [1], "3": [1]}, True, 0, 0, "Publier"),
])
def test_prochaine_action(etat_, lectures, a_jour, sans, arb, attendu):
    assert attendu in cr.prochaine_action(etat_, lectures, a_jour, sans, arb, "Q")


def test_compte_rendu_echecs_et_lecture_posterieure(racine, capsys):
    r = racine(cr, ea)
    d = passage(r)
    ecrire_json(r / "resultats/lecture-critique-2026-11-19/lecture.json", {"S": {"ecarts": []}})
    ecrire_json(r / "resultats/etat-passage-2026-11-19.json", etat(
        etapes={"synthese": {"statut": "échec", "commandes": []}}, code=1, reprise="REPRENDRE",
        echecs=[{"etape": "synthese", "commande": "python3 scripts/fusion_scripts.py", "code": 5}]))
    f = ecrire_json(r / "resultats/sources-2026-11-19/lecture_ia_lot1.json", {})
    lc = r / "resultats/lecture-critique-2026-11-19/lecture.json"
    os.utime(f, (lc.stat().st_mtime + 10,) * 2)
    code, out, _ = lancer_cr(r, capsys)
    md = (d / "compte-rendu.md").read_text(encoding="utf-8")
    assert "Commande en échec (synthese) : `python3 scripts/fusion_scripts.py`, code 5." in md
    assert "Étapes faites : aucune ; autres : synthese (échec)." in md and "Étapes non lancées dans ce passage : mesure, releve, sources" in md
    assert "Écarts tranchés : 0." in md and "Synthèse : antérieure" in md and "REPRENDRE" in out
    assert json.loads(lc.read_text(encoding="utf-8")) == {"S": {"ecarts": []}}
