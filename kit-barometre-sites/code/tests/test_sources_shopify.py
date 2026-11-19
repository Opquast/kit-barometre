"""Tests de sources_shopify.py (données publiques Shopify simulées)."""

from __future__ import annotations

import io
import json
import sys
from datetime import date
from urllib.error import HTTPError, URLError

import pytest

import sources_shopify as ss
from aide_parc import PARC_ORIGINE, poser_parc
from conftest import FausseReponse, ecrire_json, erreur_http, lire_json


@pytest.fixture(autouse=True)
def sans_attente(monkeypatch):
    monkeypatch.setattr(ss.time, "sleep", lambda s: None)
    yield
    ss.DELAI = 8.0


def scenario(monkeypatch, reponses):
    file = list(reponses)

    def urlopen(req, timeout):
        x = file.pop(0)
        if isinstance(x, Exception):
            raise x
        return x

    monkeypatch.setattr(ss, "urlopen", urlopen)


def test_get(monkeypatch):
    scenario(monkeypatch, [erreur_http(429), FausseReponse("ok", 200, "https://a.fr/")])
    assert ss.get("https://a.fr/") == (200, "https://a.fr/", "ok")
    scenario(monkeypatch, [erreur_http(429)] * 3)
    assert ss.get("https://a.fr/") == (429, "https://a.fr/", "")
    scenario(monkeypatch, [HTTPError("https://a.fr", 404, "x", {}, io.BytesIO(b"page 404"))])
    assert ss.get("https://a.fr/") == (404, "https://a.fr/", "page 404")
    scenario(monkeypatch, [URLError("dns")])
    assert ss.get("https://a.fr/")[0] == 0


def test_jsonld_et_texte():
    html = ('<script type="application/ld+json">{"@type": "Product", "offers": [{"@type": "Offer", "availability": "x/InStock"}],'
            ' "brand": {"name": "B"}}</script><script type="application/ld+json">[{"a": 1}, [{"b": 2}], 3]</script>'
            '<script type="application/ld+json">{invalide</script>')
    types = sorted(str(x.get("@type", "")) for x in ss.jsonld(html))
    assert types == ["", "", "", "Offer", "Product"]
    assert ss.texte("<style>x</style><p>a&amp;b</p>\n<script>y</script> c") == "a&b c"


def nav(n):
    return "".join(f'<a href="/collections/c{i}">C{i}</a>' for i in range(n))


POLITIQUE = lambda corps: json.dumps({"policy": {"title": "T", "body": corps}})
LONG = " Texte assez long pour être retenu comme politique de la boutique en ligne."


def test_sources_shopify_main(racine, monkeypatch, tmp_path, capsys):
    r = racine(ss)
    (r / "scripts/ecrans_en_ligne.csv").write_text(
        "service,gabarit,url\n"
        "Boutique A,Accueil,https://a.fr/\nBoutique A,Produit,https://a.fr/products/p?variant=1\nBoutique A,Article,https://a.fr/blogs/news/x\n"
        "Boutique B,Accueil,https://b.fr/\n"
        "Boutique C,Accueil,https://c.fr/fr\n"
        "Boutique D,Accueil,https://d.fr/\n"
        "Boutique E,Accueil,https://e.fr/\nBoutique E,Produit,https://e.fr/products/q\nBoutique E,Article,https://e.fr/blogs/b/y\n", encoding="utf-8")
    sortie = r / "resultats" / f"sources-{date.today():%Y-%m-%d}"
    ecrire_json(sortie / "shopify.json", {"Boutique D": {"_fini": True, "1": ["C", "", ""]}})
    pays = [f"P{i}" for i in range(10)]
    grande_404 = "<header>" + nav(4) + "x" * 6000

    def get(url):
        table = {
            "https://a.fr/meta.json": (200, url, json.dumps({"ships_to_countries": pays})),
            "https://a.fr/products/p.js": (200, url, json.dumps({"available": True, "variants": [{"available": True}, {"available": False}]})),
            "https://a.fr/products/p?variant=1": (200, url, '<script type="application/ld+json">{"@type": "Product", "offers": {"availability": "https://schema.org/InStock"}}</script>'),
            "https://a.fr/blogs/news/x": (200, url, '<script type="application/ld+json">{"datePublished": "2026-01-01"}</script>'
                                          '<time datetime="2026-01-01">x</time><meta property="article:published_time" content="2026">'),
            "https://a.fr/": (200, url, nav(4) + '<a href="/blogs/news/">Blog</a>'),
            "https://a.fr/blogs/news.atom": (200, url, "<feed><entry></entry><entry></entry></feed>"),
            "https://a.fr/policies/privacy-policy.json": (200, url, POLITIQUE("Siège : 1 rue X, 75001 Paris, France." + LONG)),
            "https://a.fr/policies/refund-policy.json": (200, url, POLITIQUE("Retours : 2 rue Y 69001 Lyon" + LONG)),
            "https://a.fr/policies/shipping-policy.json": (200, url, POLITIQUE("court")),
            "https://b.fr/meta.json": (403, url, ""),
            "https://c.fr/meta.json": (200, url, "<html>pas du json</html>"),
            "https://c.fr/fr": (200, url, '<link rel="alternate" type="application/atom+xml" href="/blogs/news.atom">' + nav(1)),
            "https://e.fr/meta.json": (200, url, "{}"),
            "https://e.fr/products/q.js": (404, url, ""),
            "https://e.fr/products/q": (200, url, '<script type="application/ld+json">{"@type": "Offer"}</script>'),
            "https://e.fr/blogs/b/y": (200, url, "<p>sans date</p>"),
            "https://e.fr/": (200, url, nav(3) + '<a href="/blogs/b">Blog</a>'),
            "https://e.fr/blogs/b.atom": (404, url, ""),
            "https://e.fr/policies/privacy-policy.json": (200, url, POLITIQUE("Adresse : 3 rue Z, 33000 Bordeaux, France." + LONG)),
        }
        if "controle-opquast" in url:
            if url.startswith("https://a.fr/"):
                return 404, url, grande_404
            if url.startswith("https://e.fr/"):
                return 404, url, "<header>" + nav(1)
            return 200, url, ""
        return table.get(url, (404, url, ""))

    monkeypatch.setattr(ss, "get", get)
    textes = tmp_path / "hors" / "textes"
    monkeypatch.setattr(sys, "argv", ["ss", str(textes), "--delai", "0"])
    assert ss.main() == 0
    assert ss.DELAI == 0
    res = lire_json(sortie / "shopify.json")
    a = res["Boutique A"]
    assert a["47"][0] == "C" and a["47"][1].endswith("…)")
    assert a["_produit"] == {"disponible": True, "variantes": 2, "indisponibles": 1}
    assert a["34"][0] == "C" and "InStock" in a["34"][1]
    assert a["231"][0] == "C" and "JSON-LD datePublished" in a["231"][1] and "<time" in a["231"][1] and "meta article" in a["231"][1]
    assert a["1"][0] == "C" and "2 entrées" in a["1"][1]
    assert a["223"][0] == "C" and a["225"][0] == "C"
    assert a["_politiques"] == ["privacy-policy", "refund-policy"]
    assert a["129"][0] == "NC"
    assert (textes / "Boutique_A__politique_privacy_policy.txt").read_text(encoding="utf-8").startswith("T\n\nSiège")
    assert res["Boutique B"] == {"_limite": "meta.json : code 403, vérification anti-robot possible : le site est laissé de côté"}
    c = res["Boutique C"]
    assert c["47"][0] == "I" and "34" not in c and "231" not in c
    assert c["1"][0] == "C" and c["223"][0] == "NC" and c["225"][0] == "I" and "129" not in c
    assert res["Boutique D"] == {"_fini": True, "1": ["C", "", ""]}
    e = res["Boutique E"]
    assert "_produit" not in e and e["34"][0] == "I" and e["231"][0] == "NC" and e["1"][0] == "I"
    assert e["223"][0] == "NC" and e["225"][0] == "NC" and e["129"][0] == "C"
    assert "politiques" in capsys.readouterr().out


def test_sources_shopify_defi(racine, monkeypatch, tmp_path):
    r = racine(ss)
    monkeypatch.setattr(ss, "get", lambda url: (200, url, "<title>challenge</title>"))
    monkeypatch.setattr(sys, "argv", ["ss", str(tmp_path / "t")])
    ss.main()
    res = lire_json(r / "resultats" / f"sources-{date.today():%Y-%m-%d}" / "shopify.json")
    assert "_limite" in res["Ma boutique"]


def test_sources_shopify_autre_plateforme(racine, monkeypatch, tmp_path, capsys):
    """Un site du parc sur une autre plateforme n'est pas interrogé ; un site absent du parc l'est (Shopify par défaut)."""
    donnees = {"sites": [dict(PARC_ORIGINE["sites"][0], plateforme="wordpress")]}
    r = poser_parc(racine, ss, donnees=donnees)
    (r / "scripts/ecrans_en_ligne.csv").write_text(
        "service,gabarit,url\nBoutique A,Accueil,https://a.fr/\nAutre,Accueil,https://z.fr/\n", encoding="utf-8")
    vus = []
    monkeypatch.setattr(ss, "get", lambda url: vus.append(url) or (403, url, ""))
    monkeypatch.setattr(sys, "argv", ["ss", str(tmp_path / "t")])
    ss.main()
    res = lire_json(r / "resultats" / f"sources-{date.today():%Y-%m-%d}" / "shopify.json")
    assert list(res) == ["Autre"] and vus == ["https://z.fr/meta.json"]
    assert "Boutique A : plateforme wordpress, sources Shopify sans objet" in capsys.readouterr().out
