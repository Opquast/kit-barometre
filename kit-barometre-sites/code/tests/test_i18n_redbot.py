"""Tests de i18n_w3c.py et redbot_local.py (services simulés)."""

from __future__ import annotations

import io
import json
import sys
from datetime import datetime
from types import SimpleNamespace

import pytest

import i18n_w3c as i18n
import redbot_local as rb
from conftest import lire_json

ECRANS = ("service,gabarit,url\n"
          "Boutique A,Accueil,https://a.fr/\nBoutique A,Panier,https://a.fr/cart\nBoutique A,Produit,https://a.fr/p\n"
          "Boutique A,Erreur,https://a.fr/x\nBoutique C,Compte,https://c.fr/account\nBoutique B,Accueil,https://b.fr/\n")


def ecrans(r):
    (r / "scripts/ecrans_en_ligne.csv").write_text(ECRANS, encoding="utf-8")


def aujourdhui():
    return f"{datetime.now().astimezone():%Y-%m-%d}"


# --- i18n_w3c ---------------------------------------------------------------

RAPPORT = """
<table><tr><td>HTML tag</td><td>fr</td><td>&lt;html lang="fr"&gt;</td></tr>
<tr><td>HTTP Content-Type</td><td>utf-8</td><td>text/html; charset=utf-8</td></tr>
<tr><td>Meta tag</td><td>utf-8</td></tr><tr><td>seule</td></tr></table>
<h2 class="title" title="rep_charset_bogus_utf16"><img src="x" alt="Warning" />Remarque <b>UTF</b></h2>
the document was run through the HTML Tidy
"""


def test_texte_et_analyser():
    assert i18n.texte("<b>a</b>&amp;\n  b") == "a & b"
    a = i18n.analyser(RAPPORT)
    assert a["info"]["HTML tag"] == ("fr", '<html lang="fr">')
    assert a["info"]["Meta tag"] == ("utf-8", "")
    assert a["remarques"] == [{"code": "rep_charset_bogus_utf16", "gravite": "Warning", "titre": "Remarque UTF"}]
    assert a["tidy"] is True


def test_statuts_conformes():
    out = {c["rule_number"]: c["status"] for c in i18n.statuts(i18n.analyser(RAPPORT))}
    assert out == {130: "conforme", 228: "conforme", 232: "conforme", 233: "conforme"}


def test_statuts_non_conformes():
    a = {"info": {"HTML tag": ("none found", ""), "HTTP Content-Type": ("None found", "text/html"),
                  "Meta tag": ("iso-8859-1", "")},
         "remarques": [{"code": "rep_lang_missing", "gravite": "Error", "titre": "Langue"},
                       {"code": "rep_charset_meta_late", "gravite": "Error", "titre": "Meta tardive"},
                       {"code": "rep_charset_utf8_only", "gravite": "Error", "titre": "UTF"}]}
    out = {c["rule_number"]: c for c in i18n.statuts(a)}
    assert {n: c["status"] for n, c in out.items()} == {130: "non-conforme", 228: "non-conforme", 232: "non-conforme", 233: "non-conforme"}
    assert "erreurs : Langue" in out[130]["comment"]
    assert "erreur W3C : Meta tardive" in out[232]["comment"]


def test_statuts_vides():
    out = {c["rule_number"]: c for c in i18n.statuts({"info": {}, "remarques": []})}
    assert out[130]["comment"] == "Attribut lang : absent"
    assert out[228]["comment"].endswith("absent")
    assert out[232]["comment"] == "Balise meta : absente"
    assert out[233]["comment"] == "Codage déclaré : aucun"


class FausseReponse(io.BytesIO):
    pass


def test_i18n_main(racine, monkeypatch, capsys):
    r = racine(i18n)
    ecrans(r)
    monkeypatch.setattr(i18n.time, "sleep", lambda s: None)
    monkeypatch.setattr(sys, "argv", ["i18n", "--delai", "0"])
    pages = {
        "https%3A%2F%2Fa.fr%2F": RAPPORT,
        "https%3A%2F%2Fa.fr%2Fcart": "<html>captcha</html>",
        "https%3A%2F%2Fa.fr%2Fp": RAPPORT.replace("utf-8</td></tr>\n<tr><td>Meta", "iso-8859-1</td></tr>\n<tr><td>Meta").replace(
            'alt="Warning"', 'alt="Error"'),
        "https%3A%2F%2Fb.fr%2F": RAPPORT,
    }

    def urlopen(req, timeout):
        cle = req.full_url.split("uri=")[1]
        if cle not in pages:
            raise OSError("refus")
        return FausseReponse(pages[cle].encode())

    monkeypatch.setattr(i18n.urllib.request, "urlopen", urlopen)
    i18n.main()
    sortie = r / "resultats" / f"i18n-{aujourdhui()}"
    res = lire_json(sortie / "resultats.json")
    a = {p["gabarit"]: p for p in res["services"]["Boutique A"]["pages"]}
    assert len(a["Accueil"]["controles"]) == 4 and a["Accueil"]["html_repare_par_tidy"] is True
    assert "protection anti-robots" in a["Panier"]["non_teste"]
    assert a["Erreur"]["non_teste"] == "i18n checker : refus"
    assert res["services"]["Boutique C"]["pages"][0]["non_teste"].startswith("compte client")
    rapport = (sortie / "rapport.md").read_text(encoding="utf-8")
    assert "| Boutique A | 2 sur 4 |" in rapport and "**1 NC** / 2" in rapport and "| 1 / 1 |" in rapport
    assert "- Error : Remarque UTF (Boutique A)" in rapport
    assert "- Boutique C, Compte : non testé" in rapport
    sortie_console = capsys.readouterr().out
    assert "non conformes : 233" in sortie_console and "| conforme" in sortie_console and "non testé (refus)" in sortie_console


def test_i18n_un_service(racine, monkeypatch):
    r = racine(i18n)
    ecrans(r)
    monkeypatch.setattr(sys, "argv", ["i18n", "--service", "Boutique C"])
    i18n.main()
    res = lire_json(r / "resultats" / f"i18n-{aujourdhui()}" / "resultats.json")
    assert list(res["services"]) == ["Boutique C"]


# --- redbot_local -----------------------------------------------------------

def test_lancer(monkeypatch):
    vu = {}

    def run(cmd, **kw):
        vu["cmd"] = cmd
        return SimpleNamespace(stdout='{"log": {}}')

    monkeypatch.setattr(rb.subprocess, "run", run)
    assert rb.lancer("https://a.fr/") == {"log": {}}
    assert vu["cmd"][1:] == ["-o", "har", "-t", "60", "https://a.fr/"]


def entetes(**h):
    return {"headers": [{"name": k.replace("_", "-"), "value": v} for k, v in h.items()]}


def test_regles_bonnes():
    notes = [{"note_id": "CONTENT_TYPE_OPTIONS"}, {"note_id": "FRAME_OPTIONS_DENY"}, {"note_id": "CONNEG_GZIP_GOOD"}, {}]
    out = {c["rule_number"]: c for c in rb.regles(notes, entetes(Cache_Control="max-age=0", Content_Type="text/html; charset=utf-8"))}
    assert {n: c["status"] for n, c in out.items()} == {206: "conforme", 211: "conforme", 226: "conforme", 227: "conforme", 228: "conforme"}
    assert "max-age=0" in out[227]["comment"]


def test_regles_mauvaises():
    out = {c["rule_number"]: c for c in rb.regles([{"note_id": "FRAME_OPTIONS_NOT"}], {})}
    assert {n: c["status"] for n, c in out.items()} == {206: "non-conforme", 211: "non-conforme", 227: "non-conforme", 228: "non-conforme"}
    assert "absent" in out[206]["comment"] and "FRAME_OPTIONS_NOT" in out[211]["comment"]


def test_regles_csp_et_encodage():
    out = {c["rule_number"]: c for c in rb.regles([], entetes(Content_Security_Policy="frame-ancestors 'self'",
                                                             Content_Encoding="br", ETag="x"))}
    assert out[211]["status"] == "conforme" and "CSP_FRAME" in out[211]["comment"]
    assert out[226]["status"] == "conforme" and "non négociée" in out[226]["comment"]
    assert out[227]["status"] == "conforme"
    sans = {c["rule_number"]: c for c in rb.regles([{"note_id": "CONNEG_NO_GZIP"}], {})}
    assert sans[226]["status"] == "non-conforme" and sans[211]["comment"].endswith("aucune")


def har(statut, notes=(), **h):
    return {"log": {"entries": [{"response": {"status": statut, **entetes(**h)}, "_red_messages": list(notes)}]}}


def test_redbot_main(racine, monkeypatch, capsys):
    r = racine(rb)
    ecrans(r)
    monkeypatch.setattr(rb.time, "sleep", lambda s: None)
    monkeypatch.setattr(sys, "argv", ["rb", "--delai", "0"])
    bonnes = [{"level": "GOOD", "note_id": "CONTENT_TYPE_OPTIONS", "summary": "ok"}, {"level": "GOOD", "note_id": "FRAME_OPTIONS_DENY"},
              {"level": "WARN", "note_id": "CONNEG_GZIP_GOOD", "summary": "w"}]
    reponses = {
        "https://a.fr/": har(200, bonnes, Cache_Control="max-age=60", Content_Type="text/html; charset=utf-8"),
        "https://a.fr/cart": har(429),
        "https://a.fr/p": har(200, [{"level": "BAD", "note_id": "X", "summary": "mauvais"}]),
        "https://b.fr/": har(None, bonnes, Cache_Control="max-age=60", Content_Type="text/html; charset=utf-8"),
    }

    def lancer(url):
        if url not in reponses:
            raise ValueError("pas de HAR")
        return reponses[url]

    monkeypatch.setattr(rb, "lancer", lancer)
    rb.main()
    sortie = r / "resultats" / f"redbot-{aujourdhui()}"
    res = lire_json(sortie / "resultats.json")
    a = {p["gabarit"]: p for p in res["services"]["Boutique A"]["pages"]}
    assert len(a["Accueil"]["controles"]) == 5
    assert a["Panier"]["non_teste"] == "code 429 (page refusée au robot)"
    assert a["Erreur"]["non_teste"] == "REDbot : pas de HAR"
    assert res["services"]["Boutique C"]["pages"][0]["non_teste"].startswith("compte client")
    assert (sortie / "har" / "boutique-a-accueil.har").exists()
    rapport = (sortie / "rapport.md").read_text(encoding="utf-8")
    assert "| Boutique A | 2 sur 4 |" in rapport and "| 1 / 1 |" in rapport
    assert "| Boutique C | 0 sur 1 |  |  |  |  |  | 0 / 0 |" in rapport
    assert "- BAD X : mauvais (1 site(s))" in rapport
    console = capsys.readouterr().out
    assert "non conformes" in console and "| conforme" in console and "non testé (pas de HAR)" in console


@pytest.mark.parametrize("service", ["Boutique B"])
def test_redbot_un_service(racine, monkeypatch, service):
    r = racine(rb)
    ecrans(r)
    monkeypatch.setattr(sys, "argv", ["rb", "--service", service])
    monkeypatch.setattr(rb, "lancer", lambda url: har(200))
    rb.main()
    res = json.loads((r / "resultats" / f"redbot-{aujourdhui()}" / "resultats.json").read_text(encoding="utf-8"))
    assert list(res["services"]) == [service]
