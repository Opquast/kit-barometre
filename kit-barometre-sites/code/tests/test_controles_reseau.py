"""Tests de controles_reseau.py (HTTP, TLS et DNS simulés)."""

from __future__ import annotations

import gzip
import json
import ssl
import subprocess
import sys
import zlib
from types import SimpleNamespace

import pytest

import controles_reseau as cr
from conftest import lire_json


# --- Client -----------------------------------------------------------------

class FausseConnexion:
    """Remplace HTTPConnection et HTTPSConnection ; les réponses viennent de la liste partagée REPONSES."""

    REPONSES: list = []
    APPELS: list = []

    def __init__(self, hote, port, timeout=None, context=None):
        self.hote, self.port, self.https = hote, port, context is not None

    def request(self, methode, chemin, headers):
        FausseConnexion.APPELS.append((self.https, self.hote, self.port, chemin, headers))
        self._rep = FausseConnexion.REPONSES.pop(0)
        if isinstance(self._rep, Exception):
            raise self._rep

    def getresponse(self):
        statut, entetes, corps = self._rep
        return SimpleNamespace(status=statut, read=lambda: corps, getheaders=lambda: list(entetes.items()))

    def close(self):
        pass


@pytest.fixture
def connexion(monkeypatch):
    FausseConnexion.REPONSES, FausseConnexion.APPELS = [], []
    monkeypatch.setattr(cr.http.client, "HTTPSConnection", FausseConnexion)
    monkeypatch.setattr(cr.http.client, "HTTPConnection", FausseConnexion)
    monkeypatch.setattr(cr.time, "sleep", lambda s: None)
    return FausseConnexion


def test_attendre(monkeypatch):
    attentes = []
    monkeypatch.setattr(cr.time, "sleep", attentes.append)
    horloge = iter([100.0, 100.0, 101.0, 101.0])
    monkeypatch.setattr(cr.time, "monotonic", lambda: next(horloge))
    c = cr.Client(5)
    c._attendre("a.fr")
    c._attendre("a.fr")
    assert len(attentes) == 1 and attentes[0] == pytest.approx(4.0)


def test_requete_redirections_et_decompression(connexion):
    connexion.REPONSES += [
        (301, {"Location": "https://a.fr/b"}, b""),
        (429, {"Retry-After": "2"}, b""),
        (429, {}, b""),
        (200, {"Content-Encoding": "gzip"}, gzip.compress(b"<html>ok</html>")),
    ]
    c = cr.Client(0)
    r = c.requete("http://a.fr/?x=1")
    assert r["statut"] == 200 and r["corps"] == b"<html>ok</html>" and r["url_finale"] == "https://a.fr/b"
    assert r["chaine"] == [("http://a.fr/?x=1", 301), ("https://a.fr/b", 200)]
    assert connexion.APPELS[0][:4] == (False, "a.fr", 80, "/?x=1")
    assert connexion.APPELS[1][:4] == (True, "a.fr", 443, "/b")
    assert any("nouvel essai dans 2 s" in x for x in c.journal) and any("dans 40 s" in x for x in c.journal)


def test_requete_deflate_corrompu_erreur_et_sans_suivre(connexion):
    connexion.REPONSES += [(200, {"Content-Encoding": "deflate"}, zlib.compress(b"d")),
                           (200, {"Content-Encoding": "gzip"}, b"pas du gzip"),
                           OSError("refus"),
                           (302, {"Location": "/x"}, b"")]
    c = cr.Client(0)
    assert c.requete("https://a.fr/")["corps"] == b"d"
    assert c.requete("https://a.fr/")["corps"] == b"pas du gzip"
    r = c.requete("https://a.fr/")
    assert r["statut"] == 0 and r["erreur"] == "refus" and "ERREUR" in c.journal[-1]
    assert c.requete("https://a.fr/", suivre=False)["statut"] == 302


def test_requete_trop_de_redirections(connexion):
    connexion.REPONSES += [(302, {"Location": "/boucle"}, b"")] * (cr.MAX_REDIRECTIONS + 1)
    r = cr.Client(0).requete("https://a.fr/", entetes={"X": "1"})
    assert r["erreur"] == "trop de redirections" and len(r["chaine"]) == cr.MAX_REDIRECTIONS + 1
    assert connexion.APPELS[0][4]["X"] == "1"


def test_requete_429_persistant(connexion):
    connexion.REPONSES += [(429, {}, b"")] * (cr.MAX_REESSAIS_429 + 1)
    assert cr.Client(0).requete("https://a.fr/")["statut"] == 429


# --- Ressources et controles_page --------------------------------------------

def test_ressources():
    a = cr.Ressources()
    a.feed('<meta charset="utf-8"><script src="http://x/a.js" integrity="sha"></script><img src="/i.png"><img>'
           '<link rel="stylesheet" href="/s.css"><link rel="alternate" href="/x"><link href="/y">')
    assert a.meta_charset and [r["url"] for r in a.ressources] == ["http://x/a.js", "/i.png", "/s.css"]
    b = cr.Ressources()
    b.feed('<meta http-equiv="Content-Type" content="text/html; charset=utf-8"><meta name="x">')
    assert b.meta_charset


def rep(entetes, corps="", statut=200, url="https://a.fr/"):
    return {"statut": statut, "entetes": entetes, "corps": corps.encode(), "octets_transferes": len(corps), "url_finale": url}


def statuts(controles):
    return {c["rule_number"]: c["status"] for c in controles}


def test_controles_page_inaccessible():
    c, poids = cr.controles_page("u", {"statut": 0, "entetes": {}, "erreur": "dns"})
    assert poids == {} and set(statuts(c).values()) == {cr.NON_TESTE}
    c, _ = cr.controles_page("u", rep({}, statut=503))
    assert "code 503" in c[0]["comment"]


def test_controles_page_bonne():
    e = {"strict-transport-security": "max-age=31536000; includeSubDomains", "x-content-type-options": "nosniff",
         "content-type": "text/html; charset=utf-8", "x-xss-protection": "1", "content-security-policy": "default-src 'self'; frame-ancestors 'self'",
         "server": "cloudflare", "content-encoding": "br", "referrer-policy": "strict-origin", "cache-control": "max-age=60"}
    corps = '<script src="https://cdn.x.fr/a.js" integrity="sha"></script><img src="/a.png"><link rel="stylesheet" href="/s.css">'
    c, poids = cr.controles_page("u", rep(e, corps))
    assert set(statuts(c).values()) == {cr.CONFORME}
    assert poids["scripts"] == 1 and poids["styles"] == 1 and poids["images"] == 1 and poids["tiers_sans_integrity"] == 0


def test_controles_page_mauvaise(monkeypatch):
    corps = '<meta charset="utf-8"><meta name="referrer" content="no-referrer"><script src="http://t.fr/a.js"></script>'
    c, _ = cr.controles_page("u", rep({"strict-transport-security": "max-age=600", "server": "Apache/2.4", "x-powered-by": "PHP",
                                        "content-security-policy": "upgrade-insecure-requests"}, corps, url="http://a.fr/"))
    s = statuts(c)
    assert s[197] == s[199] == s[200] == s[206] == s[207] == s[210] == s[211] == s[212] == s[213] == s[214] == cr.NON_CONFORME
    assert s[25] == cr.CONFORME and s[228] == cr.NON_CONFORME
    com = {x["rule_number"]: x["comment"] for x in c}
    assert "trop courte" in com[199] and "includeSubDomains absente" in com[199]
    assert "sans default-src" in com[212] and "balise meta" in com[228] and "(balise meta)" in com[25]
    c, _ = cr.controles_page("u", rep({"content-security-policy-report-only": "default-src"}))
    com = {x["rule_number"]: x["comment"] for x in c}
    assert "Report-Only" in com[212] and com[199] == "En-tête Strict-Transport-Security absent."
    assert com[228] == "Aucun jeu de caractères déclaré." and statuts(c)[214] == cr.NA
    c, _ = cr.controles_page("u", rep({}))
    assert {x["rule_number"]: x["comment"] for x in c}[212] == "Content-Security-Policy absente."

    def plante(self, texte):
        raise ValueError("HTML cassé")

    monkeypatch.setattr(cr.Ressources, "feed", plante)
    c, poids = cr.controles_page("u", rep({}, "<html"))
    assert poids["ressources_referencees"] == 0


# --- certificat, DNS, messagerie --------------------------------------------

class FauxContexte:
    def __init__(self, cert=None, erreur=None):
        self.cert, self.erreur = cert, erreur

    def wrap_socket(self, s, server_hostname):
        if self.erreur:
            raise self.erreur
        cert = self.cert

        class T:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def getpeercert(self):
                return cert

        return T()


class FausseSocket:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.mark.parametrize("fin, statut", [("Jan 01 00:00:00 2099 GMT", cr.CONFORME), ("Jan 01 00:00:00 2000 GMT", cr.NON_CONFORME)])
def test_certificat(monkeypatch, fin, statut):
    monkeypatch.setattr(cr.socket, "create_connection", lambda *a, **k: FausseSocket())
    cert = {"notAfter": fin, "issuer": ((("organizationName", "Let's Encrypt"),),)}
    monkeypatch.setattr(cr.ssl, "create_default_context", lambda: FauxContexte(cert))
    r = cr.certificat("a.fr")
    assert r["status"] == statut and "Let's Encrypt" in r["evidence"]


def test_certificat_erreurs(monkeypatch):
    monkeypatch.setattr(cr.socket, "create_connection", lambda *a, **k: FausseSocket())
    err = ssl.SSLCertVerificationError("x")
    err.verify_message = "expiré"
    monkeypatch.setattr(cr.ssl, "create_default_context", lambda: FauxContexte(erreur=err))
    assert cr.certificat("a.fr") == cr.res(198, cr.NON_CONFORME, "Certificat refusé : expiré")

    def refus(*a, **k):
        raise OSError("refusé")

    monkeypatch.setattr(cr.socket, "create_connection", refus)
    assert cr.certificat("a.fr")["status"] == cr.NON_TESTE


def test_dns_txt(monkeypatch):
    monkeypatch.setattr(cr.subprocess, "run", lambda *a, **k: SimpleNamespace(stdout='"v=spf1 " "include:x"\n\n"autre"\n'))
    assert cr.dns_txt("a.fr") == ["v=spf1 include:x", "autre"]

    def leve(*a, **k):
        raise subprocess.TimeoutExpired("dig", 15)

    monkeypatch.setattr(cr.subprocess, "run", leve)
    assert cr.dns_txt("a.fr") == []


@pytest.mark.parametrize("spf, dmarc, statut, morceau", [
    (["v=spf1 -all"], ["v=DMARC1; p=reject; rua=mailto:x@y.fr"], cr.CONFORME, "politique reject"),
    (["v=spf1 -all"], ["v=DMARC1; p=none"], cr.NON_CONFORME, "surveillance seule"),
    (["v=spf1 -all"], ["v=DMARC1; sp=none"], cr.NON_CONFORME, "politique non lue"),
    ([], [], cr.NON_CONFORME, "SPF : absent ; DMARC : absent"),
])
def test_messagerie(monkeypatch, spf, dmarc, statut, morceau):
    monkeypatch.setattr(cr, "dns_txt", lambda nom: dmarc if nom.startswith("_dmarc") else spf + ["autre"])
    r = cr.messagerie("a.fr")
    assert r["status"] == statut and morceau in r["comment"] and "x@y.fr" not in r["evidence"]


# --- controles_site ---------------------------------------------------------

class FauxClient:
    def __init__(self, table):
        self.table, self.journal = table, ["200 x"]

    def requete(self, url, suivre=True, entetes=None):
        if entetes and "Accept-Language" in entetes:
            url = "LANG " + url
        if entetes and "User-Agent" in entetes:
            url = "MOBILE " + url
        for cle, r in self.table.items():
            if cle in url:
                return r
        return {"statut": 404, "entetes": {}, "corps": b"", "url_finale": url, "chaine": [(url, 404)]}


def r_(statut=200, corps="", url="https://www.a.fr/", **k):
    return {"statut": statut, "entetes": {}, "corps": corps.encode(), "url_finale": url, "chaine": [(url, statut)], **k}


@pytest.fixture
def site(monkeypatch):
    monkeypatch.setattr(cr, "certificat", lambda h: cr.res(198, cr.CONFORME, "ok"))
    monkeypatch.setattr(cr, "messagerie", lambda d: cr.res(217, cr.CONFORME, d))


def test_controles_site_bon(site):
    accueil = '<link hreflang="fr" href="/"><link hreflang="en" href="/en"><link hreflang="x-default" href="/">'
    c = FauxClient({
        "http://www.a.fr/": r_(url="https://www.a.fr/"),
        "https://a.fr/": r_(url="https://www.a.fr/"),
        "robots.txt": r_(corps="User-agent: *\nSitemap: https://www.a.fr/sitemap.xml"),
        "controle-opquast": r_(404),
        "/cdn/shop/": r_(403),
        "LANG https://www.a.fr/": r_(corps='<html lang="en-GB">'),
        "MOBILE https://www.a.fr/": r_(url="https://www.a.fr"),
        "https://www.a.fr/": r_(corps=accueil),
    })
    s = statuts(cr.controles_site(c, "https://www.a.fr/"))
    assert all(v == cr.CONFORME for v in s.values()), s
    assert s.keys() == {198, 217, 197, 218, 219, 220, 222, 209, 221, 135}


def test_controles_site_mauvais(site):
    c = FauxClient({
        "http://a.fr/": r_(url="http://a.fr/"),
        "https://www.a.fr/": r_(0, erreur="dns"),
        "robots.txt": r_(404),
        "sitemap.xml": r_(200),
        "controle-opquast": r_(200),
        "/assets/": r_(corps="<title>Index of /assets</title>"),
        "LANG https://a.fr/": r_(corps="<html>"),
        "MOBILE https://a.fr/": r_(url="https://m.a.fr/"),
        "https://a.fr/": r_(corps='<link hreflang="fr" href="/"><link hreflang="de" href="/de">', url="https://a.fr/"),
    })
    out = cr.controles_site(c, "https://a.fr/")
    s = statuts(out)
    assert s[197] == s[218] == s[219] == s[222] == s[209] == s[221] == s[135] == cr.NON_CONFORME
    assert s[220] == cr.CONFORME
    assert "dns" in next(x["comment"] for x in out if x["rule_number"] == 218)


def test_controles_site_inaccessible(site):
    c = FauxClient({"https://a.fr/": r_(0, erreur="x"), "sitemap.xml": r_(404)})
    s = statuts(cr.controles_site(c, "https://a.fr/"))
    assert s[221] == cr.NON_TESTE and s[135] == cr.NA and s[220] == cr.NON_CONFORME


# --- synthese et main -------------------------------------------------------

def test_synthese():
    pages = [{"gabarit": "A", "controles": [cr.res(1, cr.NON_CONFORME, ""), cr.res(2, cr.NA, ""), cr.res(3, cr.NON_TESTE, ""), cr.res(4, cr.CONFORME, "")]},
             {"gabarit": "B", "controles": [cr.res(1, cr.CONFORME, ""), cr.res(2, cr.NA, ""), cr.res(3, cr.NA, ""), cr.res(4, cr.NON_TESTE, "")]}]
    agg = cr.synthese(pages)
    assert {n: a["statut"] for n, a in agg.items()} == {1: cr.NON_CONFORME, 2: cr.NA, 3: cr.NON_TESTE, 4: cr.CONFORME}
    assert agg[1]["pages_nc"] == ["A"] and agg[3]["pages_nt"] == ["A"]


def test_main_aucun_ecran(racine, monkeypatch, capsys):
    racine(cr)
    monkeypatch.setattr(sys, "argv", ["cr", "--ecrans", str(cr.RACINE / "scripts/ecrans_en_ligne.csv"), "--service", "Inconnu"])
    assert cr.main() == 1
    assert "Aucun écran" in capsys.readouterr().err


def test_main(racine, monkeypatch, tmp_path, capsys):
    racine(cr)
    ecrans = tmp_path / "ecrans.csv"
    ecrans.write_text("service,gabarit,url\nBoutique A,Accueil,https://a.fr/\nBoutique A,Panier,https://a.fr/cart\n"
                      "Boutique A,Erreur,https://a.fr/e\nBoutique B,Accueil,https://b.fr/\n", encoding="utf-8")
    sortie = tmp_path / "sortie"
    sortie.mkdir()
    (sortie / "resultats.json").write_text(json.dumps({"services": {"Boutique Z": {"pages": [], "site": []}, "Boutique A": {"vieux": 1}}}), encoding="utf-8")
    bonnes = {"strict-transport-security": "max-age=31536000; includeSubDomains", "content-type": "text/html; charset=utf-8"}
    pages = {
        "https://a.fr/": rep(bonnes, '<script src="https://cdn.t.fr/x.js"></script>'),
        "https://a.fr/cart": rep({}, "", url="http://a.fr/cart"),
        "https://a.fr/e": {"statut": 0, "entetes": {}, "erreur": "dns", "url_finale": "https://a.fr/e"},
        "https://b.fr/": rep(bonnes, "", url="https://b.fr/"),
    }

    class Client:
        def __init__(self, delai):
            self.journal = ["200 https://a.fr/"]

        def requete(self, url):
            return pages[url]

    monkeypatch.setattr(cr, "Client", Client)
    monkeypatch.setattr(cr, "controles_site", lambda client, url: [cr.res(198, cr.CONFORME, "certificat"), cr.res(197, cr.CONFORME, "redirige")])
    monkeypatch.setattr(sys, "argv", ["cr", "--ecrans", str(ecrans), "--delai", "0", "--sortie", str(sortie)])
    assert cr.main() == 0
    res = lire_json(sortie / "resultats.json")
    assert list(res["services"]) == ["Boutique Z", "Boutique A", "Boutique B"]
    mcp = {x["rule_number"]: x for x in lire_json(sortie / "mcp-boutique-a.json")}
    assert mcp[197]["comment"] == "redirige"
    assert mcp[199]["status"] == cr.NON_CONFORME and "Non conforme sur : Panier." in mcp[199]["comment"] and "Non testé sur : Erreur." in mcp[199]["comment"]
    assert mcp[214]["status"] == cr.NON_CONFORME
    mcp_b = {x["rule_number"]: x for x in lire_json(sortie / "mcp-boutique-b.json")}
    assert mcp_b[199]["comment"].startswith("Vérifié sur 1 page(s).")
    rapport = (sortie / "rapport.md").read_text(encoding="utf-8")
    assert "## Boutique A" in rapport and "non testé sur : Erreur" in rapport and "| Erreur | 0 | - | - | - | - |" in rapport
    assert "tierce(s) sur 1 avec attribut integrity" in rapport and "page(s) vérifiée(s)" in rapport
    assert "--- passage du" in (sortie / "journal.txt").read_text(encoding="utf-8")
    assert "Résultats" in capsys.readouterr().out


def test_main_sortie_par_defaut(racine, monkeypatch):
    r = racine(cr)
    monkeypatch.setattr(cr, "Client", lambda delai: SimpleNamespace(journal=[], requete=lambda url: rep({})))
    monkeypatch.setattr(cr, "controles_site", lambda client, url: [])
    monkeypatch.setattr(sys, "argv", ["cr", "--ecrans", str(r / "scripts/ecrans_en_ligne.csv")])
    assert cr.main() == 0
    assert next((r / "resultats").glob("reseau-*/rapport.md"))
