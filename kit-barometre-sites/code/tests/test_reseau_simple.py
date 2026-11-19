"""Tests de repartir_regles.py, sources_curl.py et outils_en_ligne.py (réseau simulé)."""

from __future__ import annotations

import csv
import io
import json
import sys
from datetime import date
from types import SimpleNamespace

import pytest

import outils_en_ligne as oel
import repartir_regles as rr
import sources_curl as sc
from conftest import ecrire_json, lire_json


# --- repartir_regles --------------------------------------------------------

def test_verifier():
    rr.verifier(True, "rien")
    with pytest.raises(SystemExit, match="Répartition incohérente : oups"):
        rr.verifier(False, "oups")


def test_repartir_regles(racine, capsys):
    r = racine(rr)
    ecrire_json(r / "resultats/releve-2026-11-12/decisions.json", {
        "Boutique A": {"1": ["C", "x"], "16": ["NC", "x"], "18": ["C", "x"], "2": ["NT", "x"]}})
    rr.main()
    lignes = {int(l["numero"]): l for l in csv.DictReader((r / "referentiel/repartition-regles.csv").open(encoding="utf-8"))}
    assert len(lignes) == 245
    methodes = {l["methode"] for l in lignes.values()}
    assert methodes == {"relevé", "IA", "écartée", "réseau", "page", "manuel"}
    assert lignes[33]["methode"] == "relevé" and "parcours panier" in lignes[33]["raison"]
    assert lignes[18]["methode"] == "écartée" and "Retirée le 12/11" in lignes[18]["raison"]
    assert lignes[25]["raison"].endswith("à ajouter au script réseau.")
    assert lignes[197]["raison"].startswith("Se mesure sur les échanges HTTP ou le DNS")
    assert lignes[182]["raison"] == "Couverte par axe-core (WCAG)."
    assert lignes[3]["methode"] == "page" and "code de la page" in lignes[3]["raison"]
    assert "245" in capsys.readouterr().out


def test_repartir_regles_incoherente(racine, monkeypatch):
    racine(rr)
    monkeypatch.setattr(rr, "IA", {1: "x"})
    with pytest.raises(SystemExit, match="1 règles IA au lieu de 20"):
        rr.main()


# --- sources_curl -----------------------------------------------------------

def sortie_curl(entetes: str, corps: str, finale: str, code: int) -> str:
    return f"{entetes}\r\n\r\n{corps}\n__FIN__{finale} {code}"


def test_curl(monkeypatch):
    monkeypatch.setattr(sc.time, "sleep", lambda s: None)
    texte = sortie_curl("HTTP/1.1 301 Moved\r\nLocation: /b\r\n\r\nHTTP/2 200\r\nContent-Type: text/html\r\nServer: nginx",
                        "<html>corps</html>", "https://a.fr/b", 200)
    monkeypatch.setattr(sc.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout=texte))
    ent, corps, finale, code = sc.curl("https://a.fr/")
    assert ent == {"content-type": "text/html", "server": "nginx"}
    assert corps.strip() == "<html>corps</html>"
    assert (finale, code) == ("https://a.fr/b", 200)


def test_curl_sans_reponse(monkeypatch):
    monkeypatch.setattr(sc.time, "sleep", lambda s: None)
    monkeypatch.setattr(sc.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout="\n__FIN__ "))
    assert sc.curl("https://a.fr/") == ({}, "", "", 0)


def faux_curl(scenario):
    def curl(url, *opts):
        for cle, reponse in scenario.items():
            if cle(url, opts):
                return reponse
        raise AssertionError(f"appel inattendu {url} {opts}")
    return curl


def test_sources_curl_site_bavard(racine, monkeypatch, capsys):
    r = racine(sc)
    (r / "scripts/ecrans_en_ligne.csv").write_text(
        "service,gabarit,url\nA,Accueil,https://www.a.fr/\nA,Panier,https://www.a.fr/cart\n", encoding="utf-8")
    corps = ('<meta name="referrer" content="origin"><link rel=x hreflang="en"><link hreflang="fr-FR"><link hreflang="x-default">'
             '<script src="https://cdn.a.fr/app.js"></script><img src="//cdn.a.fr/logo.png">')
    monkeypatch.setattr(sc, "curl", faux_curl({
        lambda u, o: u == "https://www.a.fr/" and not o: ({"server": "Apache/2.4", "x-powered-by": "PHP/8"}, corps, "https://www.a.fr/", 200),
        lambda u, o: "-I" in o and u.endswith("app.js"): ({}, "", "", 200),
        lambda u, o: "-I" in o and u.endswith("logo.png"): ({"content-type": "image/png"}, "", "", 200),
        lambda u, o: u == "https://a.fr/": ({}, "", "https://a.fr/", 0),
        lambda u, o: MOBILE_ou(o): ({}, "", "https://m.a.fr/", 200),
        lambda u, o: any("Accept-Language: en" in x for x in o): ({}, '<html lang="fr">', "https://www.a.fr/", 200),
        lambda u, o: u == "https://www.a.fr/cdn/shop/": ({}, "<title>Index of /cdn/shop</title>", "", 200),
        lambda u, o: True: ({}, "", "", 404),
    }))
    sc.main()
    res = lire_json(r / "resultats" / f"sources-{date.today():%Y-%m-%d}" / "curl.json")["A"]
    assert res["25"][:2] == ["C", "Referrer-Policy : origin (meta)"]
    assert res["210"][0] == "NC"
    assert res["213"][0] == "NC" and "PHP/8" in res["213"][1]
    assert res["207"][0] == "NC" and "page HTML" in res["207"][1] and "app.js" in res["207"][1]
    assert res["218"][0] == "NC"
    assert res["221"][0] == "NC"
    assert res["135"][0] == "NC" and "« en »" in res["135"][1]
    assert res["209"] == ["NC", "listage affiché : /cdn/shop/", "curl"]
    assert "A {" in capsys.readouterr().out


def MOBILE_ou(opts):
    return sc.MOBILE in opts


def test_sources_curl_site_propre(racine, monkeypatch):
    r = racine(sc)
    (r / "scripts/ecrans_en_ligne.csv").write_text("service,gabarit,url\nB,Accueil,https://b.fr/\n", encoding="utf-8")
    ent = {"referrer-policy": "strict-origin", "content-security-policy": "default-src", "server": "cloudflare", "content-type": "text/html"}
    monkeypatch.setattr(sc, "curl", faux_curl({
        lambda u, o: u == "https://b.fr/" and not o: (ent, '<html lang="fr"><link hreflang="fr">', "https://b.fr/", 200),
        lambda u, o: u == "https://www.b.fr/": ({}, "", "https://b.fr/", 301),
        lambda u, o: MOBILE_ou(o): ({}, "", "https://b.fr", 200),
        lambda u, o: True: ({}, "page", "", 200),
    }))
    sc.main()
    res = lire_json(r / "resultats" / f"sources-{date.today():%Y-%m-%d}" / "curl.json")["B"]
    assert [res[k][0] for k in ("25", "210", "213", "207", "218", "221", "135", "209")] == ["C", "C", "C", "C", "C", "C", "NA", "C"]
    assert "aucune version" in res["213"][1]


def test_sources_curl_langue_servie(racine, monkeypatch):
    r = racine(sc)
    (r / "scripts/ecrans_en_ligne.csv").write_text("service,gabarit,url\nC,Accueil,https://c.fr/\n", encoding="utf-8")
    monkeypatch.setattr(sc, "curl", faux_curl({
        lambda u, o: u == "https://c.fr/" and not o: ({}, '<link hreflang="de"><link hreflang="fr">', "https://c.fr/", 200),
        lambda u, o: any("Accept-Language: de" in x for x in o): ({}, '<html lang="de-DE">', "https://c.fr/de", 200),
        lambda u, o: True: ({}, "", "", 404),
    }))
    sc.main()
    res = lire_json(r / "resultats" / f"sources-{date.today():%Y-%m-%d}" / "curl.json")["C"]
    assert res["135"][0] == "C"


# --- outils_en_ligne --------------------------------------------------------

class FausseReponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_get(monkeypatch):
    vu = {}

    def urlopen(req, timeout):
        vu["methode"], vu["timeout"] = req.get_method(), timeout
        return FausseReponse(b'{"ok": 1}')

    monkeypatch.setattr(oel.urllib.request, "urlopen", urlopen)
    assert oel.get("https://x.fr", "POST", 5) == {"ok": 1}
    assert vu == {"methode": "POST", "timeout": 5}


@pytest.mark.parametrize("penalites, attendu", [
    ({"a": {"result": "r", "score_modifier": -5}, "b": {"result": "r", "score_modifier": 10},
      "c": {"result": "sri-not-implemented-and-external-scripts-not-loaded-securely", "score_modifier": -50},
      "d": {"result": "r", "score_modifier": 0}}, 105),
    ({"a": {"result": "r", "score_modifier": -20}, "b": {"result": "r", "score_modifier": 5}}, 80),
    ({"a": {"result": "r", "score_modifier": -200}}, 0),
])
def test_observatory(monkeypatch, penalites, attendu):
    def get(url, methode="GET"):
        if "scan" in url:
            return {"grade": "B", "score": 70}
        return {"tests": penalites}
    monkeypatch.setattr(oel, "get", get)
    r = oel.observatory("a.fr")
    assert r["grade"] == "B" and r["score_corrige"] == attendu


def test_observatory_sans_tests(monkeypatch):
    monkeypatch.setattr(oel, "get", lambda url, methode="GET": {})
    assert oel.observatory("a.fr")["score_corrige"] == 100


def test_ssllabs(monkeypatch):
    reponses = iter([{"status": "IN_PROGRESS"}, {"status": "READY", "endpoints": [{"grade": "A"}, {"grade": "A+"}, {}]}])
    monkeypatch.setattr(oel, "get", lambda url: next(reponses))
    monkeypatch.setattr(oel.time, "sleep", lambda s: None)
    r = oel.ssllabs("a.fr")
    assert r["notes"] == ["?", "A", "A+"] and r["serveurs"] == 3 and r["statut"] == "READY"


def test_ssllabs_jamais_pret(monkeypatch):
    monkeypatch.setattr(oel, "get", lambda url: {"status": "DNS"})
    monkeypatch.setattr(oel.time, "sleep", lambda s: None)
    assert oel.ssllabs("a.fr")["statut"] == "DNS"


def test_nu(monkeypatch):
    msgs = [{"type": "error", "message": "Bad value “x” for"}, {"type": "error", "message": "Bad value “y” for"},
            {"type": "info", "subType": "warning", "message": "w"}, {"type": "info", "message": "i"}]
    monkeypatch.setattr(oel, "get", lambda url: {"messages": msgs})
    r = oel.nu("https://a.fr/p?q=1")
    assert r["erreurs"] == 2 and r["avertissements"] == 1 and r["principales"] == [("Bad value", 2)]
    assert "https%3A%2F%2Fa.fr%2Fp%3Fq%3D1" in r["details_url"]


@pytest.mark.parametrize("messages, texte", [([], "réponse vide"), ([{"type": "non-document-error", "message": "refus"}], "refus")])
def test_nu_page_non_lue(monkeypatch, messages, texte):
    monkeypatch.setattr(oel, "get", lambda url: {"messages": messages})
    with pytest.raises(RuntimeError, match=texte):
        oel.nu("https://a.fr")


def test_outils_en_ligne_main(racine, monkeypatch, capsys):
    r = racine(oel)
    (r / "scripts/ecrans_en_ligne.csv").write_text(
        "service,gabarit,url\nA,Accueil,https://a.fr/\nA,Panier,https://a.fr/cart\nA,Produit,https://a.fr/p\n"
        "B,Accueil,https://b.fr/\n", encoding="utf-8")
    sortie = r / "resultats" / f"outils-{date.today():%Y-%m-%d}"
    ecrire_json(sortie / "en_ligne.json", {
        "A": {"hote": "a.fr", "ssllabs": {"statut": "READY"}, "nu": {"https://a.fr/": {"erreurs": 0}, "https://a.fr/p": {"erreur": "x"}}},
        "B": {"hote": "b.fr", "ssllabs": {"erreur": "avant"}}})
    monkeypatch.setattr(oel.time, "sleep", lambda s: None)
    monkeypatch.setattr(sys, "argv", ["oel"])

    def ssl(h):
        raise OSError("hors ligne")

    def nu(url):
        if url.endswith("cart"):
            raise RuntimeError("refus")
        return {"erreurs": 3}

    monkeypatch.setattr(oel, "ssllabs", ssl)
    monkeypatch.setattr(oel, "nu", nu)
    oel.main()
    res = lire_json(sortie / "en_ligne.json")
    assert res["A"]["ssllabs"] == {"statut": "READY"}
    assert res["B"]["ssllabs"] == {"erreur": "hors ligne"}
    assert res["A"]["nu"]["https://a.fr/"] == {"erreurs": 0}
    assert res["A"]["nu"]["https://a.fr/cart"] == {"gabarit": "Panier", "erreur": "refus"}
    assert res["A"]["nu"]["https://a.fr/p"] == {"gabarit": "Produit", "erreurs": 3}
    assert res["B"]["nu"]["https://b.fr/"]["erreurs"] == 3
    assert str(sortie / "en_ligne.json") in capsys.readouterr().out


def test_outils_en_ligne_sans_nu(racine, monkeypatch):
    r = racine(oel)
    monkeypatch.setattr(oel.time, "sleep", lambda s: None)
    monkeypatch.setattr(sys, "argv", ["oel", "--sans-nu"])
    monkeypatch.setattr(oel, "ssllabs", lambda h: {"statut": "READY"})
    oel.main()
    res = json.loads((r / "resultats" / f"outils-{date.today():%Y-%m-%d}" / "en_ligne.json").read_text(encoding="utf-8"))
    assert res == {"Ma boutique": {"hote": "www.exemple-boutique.fr", "ssllabs": {"statut": "READY"}}}
