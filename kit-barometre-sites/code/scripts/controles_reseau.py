#!/usr/bin/env python3
"""Contrôles réseau déterministes du baromètre Opquast (couche « automatique »).

Ce script vérifie, sans navigateur et sans IA, les règles Opquast qui se mesurent
sur les échanges HTTP : HTTPS, certificat, en-têtes de sécurité, compression,
cache, jeu de caractères, robots.txt, sitemap, page 404, authentification du
domaine de messagerie. Il mesure aussi le poids du HTML de chaque page.

Même entrée, même résultat : c'est la couche déterministe de la note de cadrage.

Usage :
    python3 scripts/controles_reseau.py                       # écrans de scripts/ecrans_en_ligne.csv
    python3 scripts/controles_reseau.py --service "Boutique A"
    python3 scripts/controles_reseau.py --delai 10            # secondes entre deux requêtes au même site

Résultats : resultats/reseau-AAAA-MM-JJ/ (rapport.md, resultats.json et un
fichier par service au format attendu par generate_audit_report du MCP Opquast).

Règles de prudence : un seul site à la fois, une requête toutes les --delai
secondes (8 par défaut), respect de l'en-tête Retry-After en cas de code 429,
identification honnête du robot. Aucune commande, aucun formulaire envoyé :
uniquement des requêtes GET de lecture.

Bibliothèque standard Python uniquement (aucune dépendance à installer).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import http.client
import json
import re
import secrets
import socket
import ssl
import subprocess
import sys
import time
import zlib
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

VERSION = "0.3.0"
UA = f"Opquast-barometre-Colorz/{VERSION} (controles reseau, lecture seule)"
HSTS_MIN = 31_536_000  # un an, en secondes
RACINE = Path(__file__).resolve().parent.parent
TIMEOUT = 20
MAX_REDIRECTIONS = 6
MAX_REESSAIS_429 = 3

# Libellés des règles contrôlées (référentiel Opquast V5 « qualite-numerique »).
REGLES = {
    197: "Toutes les pages utilisent le protocole HTTPS.",
    198: "Les certificats de sécurité sont signés et en cours de validité.",
    199: "Les pages utilisant HTTPS ont un entête de transport strict.",
    200: "Les pages utilisant le protocole HTTPS ne proposent pas de ressources HTTP.",
    25: "Les entêtes envoyés par le serveur spécifient la politique de communication des referrers.",
    135: "Le serveur respecte l'ordre préférentiel de langues des outils de consultation.",
    209: "Le serveur n'envoie pas la liste des fichiers des répertoires n'ayant pas de page d'index.",
    221: "Le serveur ne force pas la redirection vers la version ou l'application mobile.",
    206: "Les entêtes envoyés par le serveur désactivent la détection automatique du type MIME de chaque ressource.",
    207: "Le serveur indique le type MIME de chaque ressource.",
    210: "Le serveur envoie les informations d'activation de protection cross site scripting.",
    211: "Le serveur envoie les informations indiquant les domaines autorisés à intégrer ses pages dans des cadres.",
    212: "Un mécanisme de sécurité restreint l'origine des contenus.",
    213: "Le serveur ne communique pas d'informations sur les logiciels et langages utilisés.",
    214: "Le contrôle d'intégrité des ressources tierces est présent et valide.",
    217: "Le domaine de messagerie est authentifié.",
    218: "L'adresse du site fonctionne avec et sans préfixe www.",
    219: "La racine du site contient des instructions pour les robots d'indexation.",
    220: "Le site propose un fichier sitemap indiquant les contenus à explorer.",
    222: "Le serveur envoie un code HTTP 404 pour les ressources non trouvées.",
    226: "Le serveur transmet des contenus compressés aux clients qui les acceptent.",
    227: "Le serveur envoie les informations permettant la mise en cache des contenus.",
    228: "Les entêtes envoyés par le serveur contiennent les informations relatives au jeu de caractères employé.",
}

CONFORME, NON_CONFORME, NA, NON_TESTE, INDETERMINE = (
    "conforme", "non-conforme", "non-applicable", "non-testé", "indéterminé")


# --------------------------------------------------------------------------- HTTP

class Client:
    """Client HTTP minimal : suit les redirections, espace les requêtes par site, gère le 429."""

    def __init__(self, delai: float):
        self.delai = delai
        self.derniere: dict[str, float] = {}
        self.journal: list[str] = []

    def _attendre(self, hote: str) -> None:
        reste = self.delai - (time.monotonic() - self.derniere.get(hote, 0.0))
        if reste > 0:
            time.sleep(reste)
        self.derniere[hote] = time.monotonic()

    def requete(self, url: str, suivre: bool = True, entetes: dict | None = None) -> dict:
        """GET d'une URL. Renvoie statut final, en-têtes, corps décompressé, chaîne de redirections."""
        chaine = []
        for _ in range(MAX_REDIRECTIONS + 1):
            rep = self._une_requete(url, entetes)
            chaine.append((url, rep["statut"]))
            if suivre and rep["statut"] in (301, 302, 303, 307, 308) and rep["entetes"].get("location"):
                url = urljoin(url, rep["entetes"]["location"])
                continue
            rep["url_finale"] = url
            rep["chaine"] = chaine
            return rep
        rep["url_finale"] = url
        rep["chaine"] = chaine
        rep["erreur"] = "trop de redirections"
        return rep

    def _une_requete(self, url: str, extra: dict | None = None) -> dict:
        p = urlsplit(url)
        chemin = (p.path or "/") + (f"?{p.query}" if p.query else "")
        for essai in range(MAX_REESSAIS_429 + 1):
            self._attendre(p.hostname or "")
            try:
                if p.scheme == "https":
                    cnx = http.client.HTTPSConnection(p.hostname, p.port or 443, timeout=TIMEOUT,
                                                      context=ssl.create_default_context())
                else:
                    cnx = http.client.HTTPConnection(p.hostname, p.port or 80, timeout=TIMEOUT)
                cnx.request("GET", chemin, headers={
                    "User-Agent": UA,
                    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate",
                    "Accept-Language": "fr-FR,fr;q=0.9",
                    **(extra or {}),
                })
                r = cnx.getresponse()
                brut = r.read()
                entetes = {k.lower(): v for k, v in r.getheaders()}
                cnx.close()
            except (OSError, http.client.HTTPException, ssl.SSLError) as e:
                self.journal.append(f"ERREUR {url} : {e}")
                return {"statut": 0, "entetes": {}, "corps": b"", "octets_transferes": 0, "erreur": str(e)}
            self.journal.append(f"{r.status} {url}")
            if r.status == 429 and essai < MAX_REESSAIS_429:
                attente = entetes.get("retry-after", "")
                attente = min(int(attente), 60) if attente.isdigit() else 20 * (essai + 1)
                self.journal.append(f"   429 : nouvel essai dans {attente} s")
                time.sleep(attente)
                continue
            codage = entetes.get("content-encoding", "").lower()
            try:
                corps = gzip.decompress(brut) if codage == "gzip" else (
                    zlib.decompress(brut) if codage == "deflate" else brut)
            except (OSError, zlib.error):
                corps = brut
            return {"statut": r.status, "entetes": entetes, "corps": corps, "octets_transferes": len(brut)}
        return {"statut": 429, "entetes": {}, "corps": b"", "octets_transferes": 0, "erreur": "429 persistant"}


# --------------------------------------------------------------------------- HTML

class Ressources(HTMLParser):
    """Relève les ressources chargées par la page (scripts, styles, images, cadres) et le meta charset."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ressources: list[dict] = []
        self.meta_charset = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and ("charset" in a or "charset=" in (a.get("content") or "").lower()):
            self.meta_charset = True
        cible = None
        if tag in ("script", "img", "iframe", "source", "video", "audio") and a.get("src"):
            cible = a["src"]
        elif tag == "link" and a.get("href") and (a.get("rel") or "").lower() in ("stylesheet", "preload", "modulepreload", "icon"):
            cible = a["href"]
        if cible:
            self.ressources.append({"balise": tag, "url": cible, "integrity": bool(a.get("integrity"))})


# --------------------------------------------------------------------------- contrôles

def res(regle: int, statut: str, commentaire: str, preuve: str = "") -> dict:
    return {"rule_number": regle, "status": statut, "comment": commentaire, "evidence": preuve}


def controles_page(url: str, rep: dict) -> tuple[list[dict], dict]:
    e = rep["entetes"]
    out: list[dict] = []
    if rep.get("erreur") or rep["statut"] == 0:
        return [res(n, NON_TESTE, f"Page inaccessible : {rep.get('erreur')}") for n in
                (25, 197, 199, 200, 206, 207, 210, 211, 212, 213, 214, 226, 227, 228)], {}
    if rep["statut"] >= 400:
        return [res(n, NON_TESTE, f"La page renvoie le code {rep['statut']}") for n in
                (25, 197, 199, 200, 206, 207, 210, 211, 212, 213, 214, 226, 227, 228)], {}

    finale = rep["url_finale"]
    https = finale.startswith("https://")
    out.append(res(197, CONFORME if https else NON_CONFORME,
                   "Page servie en HTTPS." if https else "Page servie en HTTP.", f"URL finale : {finale}"))

    hsts = e.get("strict-transport-security", "")
    m = re.search(r"max-age\s*=\s*(\d+)", hsts)
    # v0.2.0 : comme le robot d'eServices Manager, durée d'au moins un an (31 536 000 s).
    age = int(m.group(1)) if m else 0
    if not m:
        com199 = "En-tête Strict-Transport-Security absent."
    elif age < HSTS_MIN:
        com199 = f"En-tête HSTS présent mais durée trop courte : {age} s (environ {age // 86400} jours), il faut au moins un an."
    else:
        com199 = f"En-tête HSTS présent, durée d'au moins un an ({age} s)."
    if m and "includesubdomains" not in hsts.lower():
        com199 += " Directive includeSubDomains absente (recommandée)."
    out.append(res(199, CONFORME if age >= HSTS_MIN else NON_CONFORME, com199,
                   f"Strict-Transport-Security: {hsts}" if hsts else ""))

    texte = rep["corps"].decode("utf-8", errors="replace")
    analyse = Ressources()
    try:
        analyse.feed(texte)
    except Exception:  # HTML très mal formé : on garde ce qui a été lu  # nosec B110: HTML mal formé, lecture partielle voulue
        pass
    http_res = [r["url"] for r in analyse.ressources if r["url"].startswith("http://")]
    out.append(res(200, NON_CONFORME if http_res else CONFORME,
                   f"{len(http_res)} ressource(s) chargée(s) en HTTP." if http_res else "Aucune ressource chargée en HTTP.",
                   "\n".join(http_res[:5])))

    nosniff = e.get("x-content-type-options", "").lower() == "nosniff"
    out.append(res(206, CONFORME if nosniff else NON_CONFORME,
                   "X-Content-Type-Options: nosniff présent." if nosniff else "X-Content-Type-Options: nosniff absent."))

    ct = e.get("content-type", "")
    out.append(res(207, CONFORME if ct else NON_CONFORME, f"Content-Type : {ct or 'absent'}."))

    xss = e.get("x-xss-protection")
    out.append(res(210, CONFORME if xss else NON_CONFORME,
                   f"X-XSS-Protection : {xss}." if xss else
                   "X-XSS-Protection absent. Note : en-tête ignoré par les navigateurs récents, remplacé par la CSP (règle 212).")
               )

    csp = e.get("content-security-policy", "")
    xfo = e.get("x-frame-options", "")
    cadres = bool(xfo) or "frame-ancestors" in csp
    out.append(res(211, CONFORME if cadres else NON_CONFORME,
                   f"X-Frame-Options : {xfo or 'absent'} ; frame-ancestors dans la CSP : {'oui' if 'frame-ancestors' in csp else 'non'}."))

    restreint = bool(re.search(r"(^|;)\s*(default-src|script-src)\b", csp))
    if restreint:
        com212 = "La CSP restreint l'origine des contenus (default-src ou script-src)."
    elif csp:
        com212 = ("CSP présente mais sans default-src ni script-src : elle ne restreint pas l'origine des scripts "
                  "et des contenus (elle sert ici à d'autres protections).")
    elif e.get("content-security-policy-report-only"):
        com212 = "Seulement Content-Security-Policy-Report-Only (observation, sans blocage)."
    else:
        com212 = "Content-Security-Policy absente."
    out.append(res(212, CONFORME if restreint else NON_CONFORME, com212, csp[:300]))

    fuites = []
    if re.search(r"\d", e.get("server", "")):
        fuites.append(f"Server: {e['server']}")
    for cle in ("x-powered-by", "x-aspnet-version", "x-generator"):
        if e.get(cle):
            fuites.append(f"{cle}: {e[cle]}")
    out.append(res(213, NON_CONFORME if fuites else CONFORME,
                   "Le serveur annonce un logiciel ou une version." if fuites else
                   f"Aucune version annoncée (Server : {e.get('server', 'absent')}).", "\n".join(fuites)))

    hote = urlsplit(finale).hostname or ""
    tierces = [r for r in analyse.ressources if r["balise"] in ("script", "link")
               and urlsplit(urljoin(finale, r["url"])).hostname not in (hote, None)]
    avec = [r for r in tierces if r["integrity"]]
    if not tierces:
        out.append(res(214, NA, "Aucun script ni style tiers."))
    else:
        out.append(res(214, CONFORME if len(avec) == len(tierces) else NON_CONFORME,
                       f"{len(avec)} ressource(s) tierce(s) sur {len(tierces)} avec attribut integrity.",
                       "\n".join(sorted({urlsplit(urljoin(finale, r['url'])).hostname for r in tierces if not r['integrity']})[:10])))

    codage = e.get("content-encoding", "")
    out.append(res(226, CONFORME if codage in ("gzip", "br", "deflate", "zstd") else NON_CONFORME,
                   f"Content-Encoding : {codage or 'aucun'} (client acceptant gzip et deflate)."))

    # 25 (v0.3.0) : politique de referrer, par en-tête ou par balise meta
    rp = e.get("referrer-policy", "")
    meta_rp = re.search(r'<meta[^>]+name=["\']referrer["\'][^>]*content=["\']([^"\']+)', rep["corps"].decode("utf-8", "replace"), re.I)
    out.append(res(25, CONFORME if rp or meta_rp else NON_CONFORME,
                   f"Politique de referrer : {rp or (meta_rp.group(1) + ' (balise meta)' if meta_rp else 'absente')}."))

    cache = {k: e[k] for k in ("cache-control", "etag", "last-modified", "expires") if e.get(k)}
    out.append(res(227, CONFORME if cache else NON_CONFORME,
                   "Informations de cache présentes." if cache else "Aucune information de cache.",
                   "\n".join(f"{k}: {v}" for k, v in cache.items())))

    charset = "charset=" in ct.lower()
    out.append(res(228, CONFORME if charset else NON_CONFORME,
                   "Jeu de caractères dans l'en-tête Content-Type." if charset else
                   ("Jeu de caractères seulement dans la balise meta, pas dans l'en-tête." if analyse.meta_charset
                    else "Aucun jeu de caractères déclaré.")))

    poids = {
        "html_transfere_octets": rep["octets_transferes"],
        "html_decompresse_octets": len(rep["corps"]),
        "ressources_referencees": len(analyse.ressources),
        "scripts": sum(1 for r in analyse.ressources if r["balise"] == "script"),
        "styles": sum(1 for r in analyse.ressources if r["balise"] == "link"),
        "images": sum(1 for r in analyse.ressources if r["balise"] in ("img", "source")),
        "tiers_sans_integrity": len(tierces) - len(avec),
    }
    return out, poids


def certificat(hote: str) -> dict:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hote, 443), timeout=TIMEOUT) as s, ctx.wrap_socket(s, server_hostname=hote) as t:
            c = t.getpeercert()
        fin = dt.datetime.strptime(c["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=dt.timezone.utc)
        jours = (fin - dt.datetime.now(dt.timezone.utc)).days
        emetteur = dict(x[0] for x in c.get("issuer", ())).get("organizationName", "?")
        return res(198, CONFORME if jours > 0 else NON_CONFORME,
                   f"Certificat valide (vérifié par la chaîne de confiance), expire dans {jours} jours.",
                   f"Émetteur : {emetteur} ; fin : {fin.date()}")
    except ssl.SSLCertVerificationError as e:
        return res(198, NON_CONFORME, f"Certificat refusé : {e.verify_message}")
    except OSError as e:
        return res(198, NON_TESTE, f"Connexion TLS impossible : {e}")


def dns_txt(nom: str) -> list[str]:
    try:
        sortie = subprocess.run(["dig", "+short", "TXT", nom], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [l.replace('" "', "").strip('"') for l in sortie.splitlines() if l.strip()]


def messagerie(domaine: str) -> dict:
    spf = [t for t in dns_txt(domaine) if t.lower().startswith("v=spf1")]
    dmarc = [t for t in dns_txt(f"_dmarc.{domaine}") if t.lower().startswith("v=dmarc1")]
    # v0.2.0 : comme le robot d'eServices Manager, la politique DMARC doit agir (quarantine ou reject) :
    # p=none ne fait que surveiller et ne bloque aucun e-mail usurpé.
    pol = re.search(r"(?:^|;)\s*p\s*=\s*(\w+)", dmarc[0], re.I).group(1).lower() if dmarc and re.search(r"(?:^|;)\s*p\s*=", dmarc[0], re.I) else ""
    statut = CONFORME if spf and pol in ("quarantine", "reject") else NON_CONFORME
    detail = f"politique {pol or 'non lue'}" + (" (surveillance seule, aucun e-mail usurpé bloqué)" if pol == "none" else "")
    # Les adresses de réception des rapports DMARC (rua, ruf) sont masquées : pas de donnée client dans les résultats.
    preuve = re.sub(r"mailto:[^;,\s]+", "mailto:[masqué]", "\n".join((spf[:1] or []) + (dmarc[:1] or [])))
    return res(217, statut,
               f"SPF : {'présent' if spf else 'absent'} ; DMARC : {'présent, ' + detail if dmarc else 'absent'}. DKIM non vérifiable sans connaître le sélecteur.",
               preuve)


def controles_site(client: Client, base: str) -> list[dict]:
    p = urlsplit(base)
    hote = p.hostname or ""
    nu = hote[4:] if hote.startswith("www.") else hote
    out = [certificat(hote), messagerie(nu)]

    # 197 au niveau du site : la version HTTP redirige-t-elle vers HTTPS ?
    r = client.requete(f"http://{hote}/")
    ok = r.get("url_finale", "").startswith("https://") and r["statut"] < 400
    out.append(res(197, CONFORME if ok else NON_CONFORME,
                   "http:// redirige vers https://." if ok else "La version http:// ne redirige pas vers https://.",
                   " -> ".join(f"{u} ({s})" for u, s in r.get("chaine", []))))

    # 218 : avec et sans www
    autre = nu if hote.startswith("www.") else f"www.{hote}"
    r2 = client.requete(f"https://{autre}/")
    ok = r2["statut"] and r2["statut"] < 400
    out.append(res(218, CONFORME if ok else NON_CONFORME,
                   f"https://{autre}/ répond ({r2['statut']})." if ok else f"https://{autre}/ ne répond pas ({r2.get('erreur') or r2['statut']}).",
                   " -> ".join(f"{u} ({s})" for u, s in r2.get("chaine", []))))

    # 219 et 220 : robots.txt et sitemap
    rob = client.requete(f"https://{hote}/robots.txt")
    texte = rob["corps"].decode("utf-8", errors="replace") if rob["statut"] == 200 else ""
    out.append(res(219, CONFORME if rob["statut"] == 200 and texte.strip() else NON_CONFORME,
                   f"robots.txt : code {rob['statut']}, {len(texte.splitlines())} lignes."))
    sitemaps = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", texte)
    if sitemaps:
        out.append(res(220, CONFORME, "Sitemap déclaré dans robots.txt.", "\n".join(sitemaps[:3])))
    else:
        sm = client.requete(f"https://{hote}/sitemap.xml")
        out.append(res(220, CONFORME if sm["statut"] == 200 else NON_CONFORME, f"/sitemap.xml : code {sm['statut']}."))

    # 222 : une adresse inexistante doit renvoyer 404
    inexistante = f"https://{hote}/controle-opquast-{secrets.token_hex(4)}"
    r4 = client.requete(inexistante)
    out.append(res(222, CONFORME if r4["statut"] == 404 else NON_CONFORME,
                   f"Adresse inexistante : code {r4['statut']}.", inexistante))

    # 209 (v0.3.0) : un répertoire sans page d'index ne doit pas lister ses fichiers
    listes = []
    for rep_ in ("/cdn/shop/", "/assets/", "/files/", "/images/"):
        r5 = client.requete(f"https://{hote}{rep_}")
        corps = r5["corps"][:20000].decode("utf-8", "replace")
        if r5["statut"] == 200 and re.search(r"<title>\s*Index of|Directory listing|Parent Directory", corps, re.I):
            listes.append(rep_)
    out.append(res(209, NON_CONFORME if listes else CONFORME,
                   ("Liste de fichiers affichée : " + ", ".join(listes)) if listes else
                   "Aucun listage de répertoire sur /cdn/shop/, /assets/, /files/ et /images/."))

    # 221 (v0.3.0) : un navigateur mobile n'est pas redirigé de force vers une version ou une application mobile
    mob = client.requete(f"https://{hote}/", entetes={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"})
    bur = client.requete(f"https://{hote}/")
    hm, hb = urlsplit(mob.get("url_finale", "")), urlsplit(bur.get("url_finale", ""))
    if not mob["statut"] or not bur["statut"]:
        out.append(res(221, NON_TESTE, "Accueil inaccessible pour la comparaison mobile et ordinateur."))
    else:
        meme = (hm.hostname, hm.path.rstrip("/")) == (hb.hostname, hb.path.rstrip("/"))
        out.append(res(221, CONFORME if meme else NON_CONFORME,
                       "Même adresse finale sur mobile et sur ordinateur." if meme else "Redirection propre au mobile.",
                       f"mobile : {mob.get('url_finale')} ; ordinateur : {bur.get('url_finale')}"))

    # 135 (v0.3.0) : le serveur suit-il l'ordre de langues du navigateur (Accept-Language) ?
    html = bur["corps"].decode("utf-8", "replace")
    langues = sorted({l.split("-")[0].lower() for l in re.findall(r'<link[^>]+hreflang=["\']([a-zA-Z-]+)["\']', html, re.I) if l.lower() != "x-default"})
    if len(langues) < 2:
        out.append(res(135, NA, "Site proposé dans une seule langue (aucune alternative hreflang) : la préférence de langue ne s'applique pas.",
                       f"hreflang : {', '.join(langues) or 'aucun'}"))
    else:
        autre = next(l for l in langues if l != "fr")
        r6 = client.requete(f"https://{hote}/", entetes={"Accept-Language": f"{autre};q=1.0,fr;q=0.1"})
        lang6 = re.search(r'<html[^>]+lang=["\']([a-zA-Z-]+)', r6["corps"].decode("utf-8", "replace"), re.I)
        ok = bool(lang6) and lang6.group(1).split("-")[0].lower() == autre
        out.append(res(135, CONFORME if ok else NON_CONFORME,
                       f"Navigateur réglé en « {autre} » d'abord : page servie en « {lang6.group(1) if lang6 else '?'} »" + ("." if ok else ", la préférence n'est pas suivie."),
                       f"langues proposées : {', '.join(langues)} ; URL finale : {r6.get('url_finale')}"))
    return out


# --------------------------------------------------------------------------- synthèse

def synthese(par_page: list[dict]) -> dict[int, dict]:
    """Agrège les statuts d'un service : non conforme si au moins une page l'est."""
    agg: dict[int, dict] = {}
    for page in par_page:
        for c in page["controles"]:
            a = agg.setdefault(c["rule_number"], {"statuts": [], "pages_nc": [], "pages_nt": []})
            a["statuts"].append(c["status"])
            if c["status"] == NON_CONFORME:
                a["pages_nc"].append(page["gabarit"])
            elif c["status"] == NON_TESTE:
                a["pages_nt"].append(page["gabarit"])
    for n, a in agg.items():
        s = a["statuts"]
        a["statut"] = (NON_CONFORME if NON_CONFORME in s else CONFORME if CONFORME in s
                       else NA if all(x == NA for x in s) else NON_TESTE)
    return agg


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ecrans", default=str(RACINE / "scripts" / "ecrans_en_ligne.csv"))
    ap.add_argument("--service", help="ne contrôler qu'un service (nom exact de la colonne service)")
    ap.add_argument("--delai", type=float, default=8.0, help="secondes entre deux requêtes au même site (défaut 8)")
    ap.add_argument("--sortie", help="dossier de résultats (défaut resultats/reseau-AAAA-MM-JJ)")
    args = ap.parse_args()

    with open(args.ecrans, encoding="utf-8") as f:
        ecrans = [l for l in csv.DictReader(f) if not args.service or l["service"] == args.service]
    if not ecrans:
        print("Aucun écran à contrôler.", file=sys.stderr)
        return 1

    debut = dt.datetime.now().astimezone()
    sortie = Path(args.sortie or RACINE / "resultats" / f"reseau-{debut:%Y-%m-%d}")
    sortie.mkdir(parents=True, exist_ok=True)
    client = Client(args.delai)

    services: dict[str, dict] = {}
    for l in ecrans:
        s = services.setdefault(l["service"], {"pages": [], "site": None})
        if s["site"] is None:
            print(f"== {l['service']} : contrôles du site", flush=True)
            s["site"] = controles_site(client, l["url"])
        print(f"   {l['gabarit']} : {l['url']}", flush=True)
        rep = client.requete(l["url"])
        controles, poids = controles_page(l["url"], rep)
        s["pages"].append({"gabarit": l["gabarit"], "url": l["url"], "statut_http": rep["statut"],
                           "url_finale": rep.get("url_finale"), "controles": controles, "poids": poids})

    # Fusion : un relancement limité à un service remplace ce service sans effacer les autres.
    precedent = sortie / "resultats.json"
    if precedent.exists():
        anciens = json.loads(precedent.read_text(encoding="utf-8")).get("services", {})
        services = {**{k: v for k, v in anciens.items() if k not in services}, **services}

    duree = round((dt.datetime.now().astimezone() - debut).total_seconds())
    meta = {"script": "scripts/controles_reseau.py", "version": VERSION, "date": debut.isoformat(timespec="seconds"),
            "delai_s": args.delai, "user_agent": UA, "duree_s": duree, "referentiel": "Opquast V5 qualite-numerique"}
    (sortie / "resultats.json").write_text(json.dumps({"meta": meta, "services": services}, ensure_ascii=False, indent=2),
                                           encoding="utf-8")
    with open(sortie / "journal.txt", "a", encoding="utf-8") as j:
        j.write(f"--- passage du {meta['date']} ({', '.join(s for s in services if any(l['service'] == s for l in ecrans))})\n")
        j.write("\n".join(client.journal) + "\n")

    # Un fichier par service, au format de generate_audit_report (MCP Opquast).
    for nom, s in services.items():
        agg = synthese(s["pages"])
        resultats = list(s["site"])
        site_regles = {r["rule_number"] for r in resultats}
        for n in sorted(agg):
            if n in site_regles:
                continue
            a = agg[n]
            com = (f"Non conforme sur : {', '.join(a['pages_nc'])}." if a["pages_nc"]
                   else f"Vérifié sur {len(a['statuts']) - len(a['pages_nt'])} page(s).")
            if a["pages_nt"]:
                com += f" Non testé sur : {', '.join(a['pages_nt'])}."
            resultats.append({"rule_number": n, "status": a["statut"], "comment": com,
                              "evidence": f"Contrôle automatique, {meta['script']} v{VERSION}, {meta['date']}"})
        slug = re.sub(r"[^a-z0-9]+", "-", nom.lower()).strip("-")
        (sortie / f"mcp-{slug}.json").write_text(json.dumps(sorted(resultats, key=lambda r: r["rule_number"]),
                                                            ensure_ascii=False, indent=2), encoding="utf-8")

    # Rapport lisible
    lignes = [f"# Contrôles réseau du {debut:%d/%m/%Y à %H:%M}", "",
              f"Script `{meta['script']}` v{VERSION}, référentiel {meta['referentiel']}, une requête toutes les {args.delai:g} s, durée {duree} s.",
              "Contrôles déterministes : même entrée, même résultat. Les autres règles relèvent de l'audit IA et humain.", ""]
    for nom, s in services.items():
        agg = synthese(s["pages"])
        site = {r["rule_number"]: r for r in s["site"]}
        toutes = sorted(set(agg) | set(site))
        nb = {k: 0 for k in (CONFORME, NON_CONFORME, NA, NON_TESTE)}
        lignes += [f"## {nom}", "", "| Règle | Intitulé | Statut | Détail |", "|---|---|---|---|"]
        for n in toutes:
            if n in site:
                st, det = site[n]["status"], site[n]["comment"]
            else:
                st = agg[n]["statut"]
                det = (f"non conforme sur : {', '.join(agg[n]['pages_nc'])}" if agg[n]["pages_nc"]
                       else f"{len(agg[n]['statuts']) - len(agg[n]['pages_nt'])} page(s) vérifiée(s)")
                if agg[n]["pages_nt"]:
                    det += f" ; non testé sur : {', '.join(agg[n]['pages_nt'])}"
                if n == 214:
                    det += " ; " + next((c["comment"] for p in s["pages"] for c in p["controles"] if c["rule_number"] == 214), "")
            nb[st] = nb.get(st, 0) + 1
            lignes.append(f"| {n} | {REGLES[n]} | {st} | {det} |")
        lignes += ["", f"Bilan : {nb[CONFORME]} conformes, {nb[NON_CONFORME]} non conformes, {nb[NA]} non applicables, {nb[NON_TESTE]} non testées sur {len(toutes)} règles contrôlées.", "",
                   "| Page | Code | HTML transféré | HTML décompressé | Ressources (scripts / styles / images) | Tiers sans integrity |",
                   "|---|---|---|---|---|---|"]
        for p in s["pages"]:
            w = p["poids"]
            if w:
                lignes.append(f"| {p['gabarit']} | {p['statut_http']} | {w['html_transfere_octets'] / 1024:.0f} Ko | "
                              f"{w['html_decompresse_octets'] / 1024:.0f} Ko | {w['ressources_referencees']} "
                              f"({w['scripts']} / {w['styles']} / {w['images']}) | {w['tiers_sans_integrity']} |")
            else:
                lignes.append(f"| {p['gabarit']} | {p['statut_http']} | - | - | - | - |")
        lignes.append("")
    lignes += ["## Limites", "",
               "- Le poids mesuré est celui du HTML seul. Le poids complet (images, scripts, polices) se mesure dans le navigateur, avec l'audit IA.",
               "- Règle 210 : l'en-tête X-XSS-Protection est ignoré par les navigateurs récents ; la CSP (règle 212) le remplace.",
               "- Règle 199 (depuis v0.2.0) : conforme seulement si la durée HSTS atteint un an, comme le robot d'eServices Manager.",
               "- Règle 217 : DKIM n'est pas vérifié, faute de connaître le sélecteur utilisé par l'outil d'envoi. Depuis v0.2.0, la politique DMARC doit être quarantine ou reject.",
               "- Règle 227 : le script vérifie la présence d'en-têtes de cache ; le robot exige aussi que la page HTML soit mise en cache, ce qui se discute sur Shopify (pages générées à chaque visite).",
               "- Les règles de sécurité qui demandent un parcours (mots de passe, 201 à 205, 208, 215, 216) et les pages d'erreur personnalisées (223 à 225) restent à vérifier dans le navigateur.",
               ""]
    (sortie / "rapport.md").write_text("\n".join(lignes), encoding="utf-8")
    print(f"\nRésultats : {sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
