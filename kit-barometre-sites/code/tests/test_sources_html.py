"""Tests de sources_html.py et sources_html2.py (pages et réseau simulés)."""

from __future__ import annotations

import sys
from datetime import date
from urllib.error import URLError

import pytest

import sources_html as sh
import sources_html2 as sh2
from conftest import FausseReponse, ecrire_json, erreur_http, lire_json


def urlopen_scenario(monkeypatch, module, reponses):
    """reponses : liste consommée dans l'ordre ; chaque élément est une FausseReponse ou une exception."""
    file = list(reponses)

    def urlopen(req, timeout):
        x = file.pop(0)
        if isinstance(x, Exception):
            raise x
        return x

    monkeypatch.setattr(module, "urlopen", urlopen)
    monkeypatch.setattr(module.time, "sleep", lambda s: None)
    return file


# --- sources_html : get -----------------------------------------------------

def test_get_ok_et_429(monkeypatch):
    urlopen_scenario(monkeypatch, sh, [erreur_http(429), FausseReponse("ok", 200, "https://a.fr/f")])
    assert sh.get("https://a.fr/", 0) == (200, "https://a.fr/f", "ok")


def test_get_429_trois_fois(monkeypatch):
    urlopen_scenario(monkeypatch, sh, [erreur_http(429)] * 3)
    assert sh.get("https://a.fr/", 0) == (429, "https://a.fr/", "")


def test_get_404_et_reseau(monkeypatch):
    urlopen_scenario(monkeypatch, sh, [erreur_http(404)])
    assert sh.get("https://a.fr/", 0) == (404, "https://a.fr/", "")
    urlopen_scenario(monkeypatch, sh, [URLError("dns")])
    assert sh.get("https://a.fr/", 0)[0] == 0


# --- sources_html : regles --------------------------------------------------

RICHE = """<html><head><title>Boutique Alpha - accueil</title><script>var a = "<a href='/x'>"</script>
<style>p{}</style></head><body oncopy="return false" oncontextmenu="return false">
<a href="#contenu">Aller au contenu</a><a href="/">Accueil</a><a href="/pages/privacy">Confidentialité</a>
<a href="/pages/cgv">CGV</a><a href="mailto:contact@exemple.fr">Écrire</a><a href="tel:0123456789">Appeler</a>
<a href="/contact">Contact</a><a href="https://x.fr" target="_blank" title="nouvel onglet">X</a>
<a href="https://y.fr" target="_blank">Y</a><a href="/login?email=a">Lien</a>
<p>Appelez le 01 23 45 67 89 ou le +33 1 23 45 67 89. 12 résultats</p>
<form method="get" action="/account/login"><input type="email" name="email">
<input type="text" name="phone" onpaste="return false"><input type="text" name="nom" autocomplete="family-name">
<input type="hidden" name="h"><input type="search" name="q"></form>
<button disabled aria-hidden="true">Ok</button><button>Autre</button>
<img src="a.png" alt=""><img src="b.png"><iframe src="https://v.fr"></iframe><iframe src=" "></iframe><embed src="e" title="t">
<video><track kind="captions"></video><video></video>
<table><caption>T</caption><tr><th>A</th></tr></table><table role="presentation"></table><table></table>
<template><a href="/cache">caché</a></template><noscript>x</noscript>
</body></html>"""

VIDE = "<html><head><title>Rien</title></head><body><track><th></th><caption></caption></table><p>Texte</p></body></html>"


def test_regles_page_riche():
    r = sh.regles("https://a.fr/search?q=x", "Recherche", RICHE, "Boutique Alpha")
    st = {k: v[0] for k, v in r.items()}
    assert st == {
        "15": "C", "46": "C", "102": "C", "155": "C", "164": "C", "145": "C", "128": "NC", "107": "C", "146": "NC",
        "95": "NC", "97": "NC", "92": "NC", "28": "NC", "98": "NC", "116": "NC", "120": "NC", "122": "NC", "237": "NC",
        "238": "NC", "242": "NC", "243": "NC", "169": "C", "170": "C", "13": "C"}
    assert "[téléphone masqué]" in r["128"][1] and "0123456789" not in r["128"][1]
    assert all(v[2] == sh.OUTIL for v in r.values())


def test_regles_page_vide():
    r = sh.regles("https://a.fr/", "Accueil", VIDE, "Boutique Alpha")
    st = {k: v[0] for k, v in r.items()}
    assert st["15"] == st["46"] == st["102"] == st["155"] == st["164"] == st["107"] == "NC"
    for n in ("145", "128", "146", "95", "97", "92", "98", "116", "120", "122", "242", "243", "13", "169", "170"):
        assert st[n] == "NA", n
    assert st["28"] == st["237"] == st["238"] == "C"


def test_regles_variantes():
    html = ('<a href="tel:+33123456789">Tél</a><input type="text" name="ville" autocomplete="address-level2">'
            '<input type="text" name="code"><button disabled>x</button><img src="a" alt="A"><embed src="e" aria-label="v">'
            '<video><track></video><table><caption>c</caption><th>h</th></table><input name="x" type="text">'
            '<a href="https://b.fr" target="_blank">Y (nouvelle fenêtre)</a>')
    r = {k: v[0] for k, v in sh.regles("https://a.fr/s", "Recherche", html, "Filatures").items()}
    assert (r["145"], r["128"], r["97"], r["95"], r["92"], r["98"], r["116"], r["120"], r["122"], r["242"], r["243"], r["146"]) == (
        "C", "C", "C", "C", "C", "C", "C", "C", "C", "C", "C", "C")
    assert r["170"] == "NC" and r["13"] == "NC" and r["102"] == "NC"
    perso_absent = {k: v[0] for k, v in sh.regles("https://a.fr/", "Accueil", '<input type="text" name="code">', "A").items()}
    assert perso_absent["97"] == "NA"


def test_analyse_fin_de_balises_orphelines():
    a = sh.Analyse()
    a.feed("</script></table></a><td>")
    assert a._ignore == 0 and a.tables == []


# --- sources_html : main ----------------------------------------------------

def test_sources_html_main(racine, monkeypatch, capsys):
    r = racine(sh)
    (r / "scripts/ecrans_en_ligne.csv").write_text(
        "service,gabarit,url\nA,Accueil,https://a.fr/\nA,Panier,https://a.fr/cart\nA,Compte,https://a.fr/account\n"
        "A,Collection,https://a.fr/c\nA,Produit,https://a.fr/p\nA,Erreur,https://a.fr/e\n", encoding="utf-8")
    sortie = r / "resultats" / f"sources-{date.today():%Y-%m-%d}"
    ecrire_json(sortie / "html.json", {"A": {"https://a.fr/": {"15": ["C", "", ""]}, "https://a.fr/e": {"_non_teste": "code 0"}}})
    reponses = {
        "https://a.fr/cart": (200, "https://a.fr/cart", RICHE),
        "https://a.fr/account": (200, "https://shopify.com/account", RICHE),
        "https://a.fr/c": (200, "https://a.fr/c", "<title>Just a moment</title>"),
        "https://a.fr/p": (200, "https://a.fr/p", ""),
        "https://a.fr/e": (404, "https://a.fr/e", ""),
    }
    monkeypatch.setattr(sh, "get", lambda url, delai: reponses[url])
    monkeypatch.setattr(sys, "argv", ["sh", "--delai", "0"])
    assert sh.main() == 0
    res = lire_json(sortie / "html.json")["A"]
    assert res["https://a.fr/"] == {"15": ["C", "", ""]}
    assert res["https://a.fr/cart"]["_gabarit"] == "Panier" and "15" in res["https://a.fr/cart"]
    assert res["https://a.fr/account"]["_non_teste"].startswith("quitte le site")
    assert res["https://a.fr/c"]["_non_teste"].startswith("vérification anti-robot")
    assert res["https://a.fr/p"]["_non_teste"] == "code 200"
    assert res["https://a.fr/e"]["_non_teste"] == "code 404"
    assert "15:C" in capsys.readouterr().out


def test_sources_html_main_sans_fichier(racine, monkeypatch):
    r = racine(sh)
    monkeypatch.setattr(sh, "get", lambda url, delai: (0, url, "erreur"))
    monkeypatch.setattr(sys, "argv", ["sh"])
    sh.main()
    assert (r / "resultats" / f"sources-{date.today():%Y-%m-%d}" / "html.json").exists()


# --- sources_html2 : get et statut_lien -------------------------------------

def test_sur():
    assert sh2.sur("https://a.fr/é x?q=1") == "https://a.fr/%C3%A9%20x?q=1"


def test_get2(monkeypatch):
    urlopen_scenario(monkeypatch, sh2, [erreur_http(429), FausseReponse("ok", 200, "https://a.fr/")])
    assert sh2.get("https://a.fr/") == (200, "https://a.fr/", "ok")
    urlopen_scenario(monkeypatch, sh2, [erreur_http(429)] * 3)
    assert sh2.get("https://a.fr/")[0] == 429
    urlopen_scenario(monkeypatch, sh2, [erreur_http(500)])
    assert sh2.get("https://a.fr/")[0] == 500
    urlopen_scenario(monkeypatch, sh2, [ValueError("url")])
    assert sh2.get("https://a.fr/") == (0, "https://a.fr/", "url")


def test_statut_lien(monkeypatch):
    urlopen_scenario(monkeypatch, sh2, [FausseReponse(status=204), erreur_http(404), OSError("x")])
    assert [sh2.statut_lien("https://a.fr/") for _ in range(3)] == [204, 404, 0]


def test_texte_et_attrs():
    assert sh2.texte("<p>a&amp;b</p>  c") == "a&b c"
    assert sh2.attrs('<a HREF="/x" title=\'t\' data-x="&quot;"') == {"href": "/x", "title": "t", "data-x": '"'}


# --- sources_html2 : regles -------------------------------------------------

RICHE2 = """<html><head><link rel="alternate" type="application/rss+xml" href="/feed">
<link rel="alternate" hreflang="fr" href="https://a.fr/produits/x"><link rel="alternate" hreflang="en-GB" href="https://a.fr/en/produits/x">
<link rel="alternate" hreflang="x-default" href="https://a.fr/"><link rel="stylesheet" href="/s.css"><link rel="stylesheet" href="/s.css">
<link rel="stylesheet" href="/absent.css"><link rel="stylesheet">
<style>a:visited{color:red} p{font-family: Brand} h1{font-family: Arial, sans-serif} .i{font-family: FontAwesome} p{text-align: justify}</style>
</head><body>
<label for="n">Nom *</label><input id="n" name="nom" required>
<input name="mail" aria-required="true"><input type="tel" name="tel" placeholder="ex. 06 12 34 56 78">
<input type="date" name="d"><input name="cp" maxlength="5" aria-label="5 caractères"><input name="v" maxlength="10">
<input name="z" maxlength="999"><input type="hidden" name="h">
<p>Écrivez à x@y.fr, appelez le 01 23 45 67 89, 75001 Paris. Conforme au RGAA. Inscrivez-vous à notre newsletter, envoyée chaque semaine.</p>
<a href="/blogs/journal">Journal</a><a href="https://ext.fr" title="lien externe">Ext</a><a href="https://ext2.fr">Ext2</a>
<a href="mailto:x@y.fr">x@y.fr</a><a href="tel:0123">Ici</a><a href="/docs/guide.pdf">Guide (PDF)</a>
<a href="/docs/a1b2c3d4e5f6.pdf">Télécharger</a><a href="/pages/archives">Archives</a><a href="#top">Haut</a><a>vide</a>
<a href="/cart/add">Panier</a><a href="/pages/mentions">Mentions</a><a href="/casse">Cassé</a>
<a href="English">English</a><a>Anglais</a><select><option>Français</option><option>Autre</option></select>
</body></html>"""


def test_regles2_page_riche(monkeypatch):
    monkeypatch.setattr(sh2, "statut_lien", lambda u: 404 if u.endswith("casse") else 200)
    css = {}
    monkeypatch.setattr(sh2, "get", lambda u: (200, u, ".x{font-family: monospace}") if u.endswith("/s.css") else (404, u, ""))
    r = sh2.regles("https://a.fr/produits/x", "Produit", RICHE2, css)
    st = {k: v[0] for k, v in r.items()}
    assert st == {"1": "C", "71": "NC", "72": "NC", "74": "NC", "105": "C", "115": "C", "133": "C", "134": "NC", "142": "NC",
                  "144": "NC", "147": "NC", "150": "NC", "152": "NC", "177": "C", "178": "C", "179": "C", "141": "C", "190": "NC",
                  "191": "NC"}
    assert "[e-mail masqué]" in r["105"][1] or "e-mail" not in r["105"][1]
    assert css == {"https://a.fr/s.css": ".x{font-family: monospace}", "https://a.fr/absent.css": ""}


def test_regles2_page_vide(monkeypatch):
    monkeypatch.setattr(sh2, "statut_lien", lambda u: 200)
    st = {k: v[0] for k, v in sh2.regles("https://a.fr/", "Accueil", "<p>Rien</p>", {}).items()}
    assert st == {"1": "NC", "71": "NA", "72": "NA", "74": "NA", "105": "NC", "115": "NA", "133": "NA", "134": "NA", "142": "NA",
                  "144": "NA", "147": "NA", "150": "NA", "241": "NA", "177": "NA", "178": "NA", "179": "NA"}


def test_regles2_variantes_conformes(monkeypatch):
    monkeypatch.setattr(sh2, "statut_lien", lambda u: 429)
    html = ("""<link hreflang="fr" href="/x"><link hreflang="de" href="/de/x"><style>a:visited{border:0}</style>"""
            """<label for="a">Nom (obligatoire)</label><input id="a" name="a" required="required">"""
            """<input type="date" name="d" placeholder="jj/mm/aaaa"><input name="m" maxlength="20" placeholder="20 caractères">"""
            """<a href="https://e.fr" class="icon-ext">E</a><a href="mailto:a@b.fr">Écrire</a>"""
            """<a href="/f/guide-utilisateur.pdf">Guide PDF</a><a href="/a">A</a><a href="/b">B</a>"""
            """<p>Newsletter mensuelle</p><a href="/pages/archive">Anciennes newsletters</a><a>Deutsch</a>"""
            """<style>p{font-family: serif}</style>""")
    st = {k: v[0] for k, v in sh2.regles("https://a.fr/x", "Page", html, {}).items()}
    for n in ("71", "72", "74", "133", "134", "142", "144", "147", "150", "152", "177", "141", "190", "191"):
        assert st[n] == "C", n
    st = {k: v[0] for k, v in sh2.regles("https://a.fr/x", "Page", '<link hreflang="fr" href="/x"><link hreflang="de" href="/autre"><p>newsletter</p><style>a{color:red}</style>', {}).items()}
    assert st["133"] == "NC" and st["134"] == "NA" and st["179"] == "NC" and st["177"] == "NC" and st["141"] == "NC"
    assert "152" not in st


# --- sources_html2 : main ---------------------------------------------------

def test_sources_html2_main(racine, monkeypatch, capsys):
    r = racine(sh2)
    (r / "scripts/ecrans_en_ligne.csv").write_text(
        "service,gabarit,url\nA,Accueil,https://a.fr/\nA,Panier,https://a.fr/cart\nA,Compte,https://a.fr/account\n"
        "A,Collection,https://a.fr/c\nA,Erreur,https://a.fr/e\n", encoding="utf-8")
    sortie = r / "resultats" / f"sources-{date.today():%Y-%m-%d}"
    ecrire_json(sortie / "html2.json", {"A": {"https://a.fr/": {"1": ["C", "", ""]}}})
    reponses = {
        "https://a.fr/cart": (200, "https://a.fr/cart", "<p>texte</p>"),
        "https://a.fr/account": (200, "https://shopify.com/account", "<p>x</p>"),
        "https://a.fr/c": (200, "https://a.fr/c", "Votre connexion doit être vérifiée"),
        "https://a.fr/e": (0, "https://a.fr/e", ""),
    }
    monkeypatch.setattr(sh2, "get", lambda url: reponses[url])
    monkeypatch.setattr(sh2, "statut_lien", lambda u: 200)
    monkeypatch.setattr(sys, "argv", ["sh2", "--delai", "0"])
    assert sh2.main() == 0
    assert sh2.DELAI == 0
    res = lire_json(sortie / "html2.json")["A"]
    assert res["https://a.fr/"] == {"1": ["C", "", ""]}
    assert res["https://a.fr/cart"]["1"][0] == "NC"
    assert res["https://a.fr/account"]["_non_teste"].startswith("quitte")
    assert res["https://a.fr/c"]["_non_teste"].startswith("vérification")
    assert res["https://a.fr/e"]["_non_teste"] == "code 0"
    assert "1:NC" in capsys.readouterr().out


@pytest.fixture(autouse=True)
def retablir_delai():
    yield
    sh2.DELAI = 6.0


def test_sources_html2_main_sans_fichier(racine, monkeypatch):
    r = racine(sh2)
    monkeypatch.setattr(sh2, "get", lambda url: (500, url, ""))
    monkeypatch.setattr(sys, "argv", ["sh2"])
    sh2.main()
    assert (r / "resultats" / f"sources-{date.today():%Y-%m-%d}" / "html2.json").exists()
