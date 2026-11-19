#!/usr/bin/env python3
"""Deuxième source « HTML brut et feuilles de style » pour les règles du relevé navigateur restées à une source (13/11).

Même principe que scripts/sources_html.py : le code envoyé par le serveur (GET, sans JavaScript), lu par un autre
analyseur que le relevé (qui lit la page rendue dans Chromium), plus les feuilles de style CSS de la page. Lecture
seule. Indépendance partielle (même auteur, autre entrée, autre code) : présentée comme telle.

Règles : 1, 71, 72, 74, 105, 115, 133, 134, 141, 142, 144, 147, 150, 152, 177, 178, 179, 190, 191, 241.

Usage : python3 scripts/sources_html2.py [--delai 6]
Sortie : resultats/sources-AAAA-MM-JJ/html2.json  { site: { url: { regle: [statut, preuve, outil] } } }
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import date
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlsplit
from urllib.request import Request, urlopen

RACINE = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
OUTIL = "HTML brut et CSS (sans JavaScript)"
TEL = re.compile(r"(?:\+33\s?|\b0)[1-9](?:[\s.-]?\d{2}){4}\b")
GEN = re.compile(r"\b(serif|sans-serif|monospace|cursive|fantasy|system-ui|ui-sans-serif|ui-serif|ui-monospace|emoji|math)\b|inherit|initial|unset|var\(|revert", re.I)
ENDO = {"english", "deutsch", "español", "espanol", "italiano", "nederlands", "português", "français", "francais", "polski", "dansk", "svenska", "norsk", "suomi", "日本語", "中文", "한국어"}
EXO_FR = {"anglais", "allemand", "espagnol", "italien", "néerlandais", "portugais", "polonais", "danois", "suédois", "norvégien", "finnois", "japonais", "chinois", "coréen"}
DELAI = 6.0


def sur(url: str) -> str:
    return quote(url, safe=":/?&=%#+,;@~!$'()*[]")


def get(url: str) -> tuple[int, str, str]:
    url = sur(url)
    time.sleep(DELAI)
    for essai in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"}), timeout=30) as r:  # nosec B310: URL http(s) du parc ou d'un service connu
                return r.status, r.geturl(), r.read().decode("utf-8", "replace")
        except HTTPError as e:
            if e.code == 429 and essai < 2:
                time.sleep(30 * (essai + 1)); continue
            return e.code, url, ""
        except (URLError, TimeoutError, OSError, ValueError) as e:
            return 0, url, str(e)
    return 429, url, ""


def statut_lien(url: str) -> int:
    url = sur(url)
    time.sleep(1.5)
    try:
        with urlopen(Request(url, method="HEAD", headers={"User-Agent": UA}), timeout=20) as r:  # nosec B310: URL http(s) du parc ou d'un service connu
            return r.status
    except HTTPError as e:
        return e.code
    except (URLError, TimeoutError, OSError, ValueError):
        return 0


def texte(h: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def attrs(tag: str) -> dict:
    return {k.lower(): unescape(v1 or v2 or "") for k, v1, v2 in re.findall(r'([\w:-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', tag)}


def regles(url: str, gabarit: str, brut: str, css_cache: dict) -> dict:
    hote = urlsplit(url).netloc
    html = re.sub(r"<(script|style|template|noscript)[^>]*>.*?</\1>", " ", brut, flags=re.S | re.I)
    styles_inline = " ".join(re.findall(r"<style[^>]*>(.*?)</style>", brut, re.S | re.I))
    liens = [(attrs(m.group(1)), texte(m.group(2))) for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html, re.S | re.I)]
    txt = texte(html)
    r: dict = {}
    def mis(n, st, preuve): r[str(n)] = [st, re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}", "[e-mail masqué]", TEL.sub("[téléphone masqué]", preuve))[:220], OUTIL]

    # 1 : nouveautés repérables (flux, rubrique « nouveautés », blog)
    flux = re.search(r'<link[^>]+type=["\']application/(atom|rss)\+xml', brut, re.I)
    nouv = [t for a, t in liens if re.search(r"nouveaut|new in|nouvelle collection|derniers? articles?|actualit|journal|blog", t + " " + a.get("href", ""), re.I)]
    mis(1, "C" if flux or nouv else "NC", "flux Atom ou RSS déclaré" if flux else f"lien « {nouv[0][:50]} »" if nouv else "aucun flux ni lien vers les nouveautés dans le HTML envoyé")

    # formulaires : 71 (obligatoire signalé), 72 (format), 74 (limite de caractères)
    labels = {attrs(m.group(1)).get("for", ""): texte(m.group(2)) for m in re.finditer(r"<label\b([^>]*)>(.*?)</label>", html, re.S | re.I)}
    champs = [attrs(m.group(0)) for m in re.finditer(r"<(input|textarea|select)\b[^>]*>", html, re.I)]
    champs = [c for c in champs if c.get("type", "text") not in ("hidden", "submit", "button", "image", "reset", "checkbox", "radio")]
    def etiquette(c): return " ".join(x for x in (labels.get(c.get("id", ""), ""), c.get("aria-label", ""), c.get("placeholder", "")) if x)
    req = [c for c in champs if "required" in c or c.get("aria-required") == "true"]
    if req:
        sans = [c.get("name", "?") for c in req if not re.search(r"\*|obligatoire|requis|required", etiquette(c), re.I)]
        mis(71, "NC" if sans else "C", f"{len(req)} champ(s) obligatoire(s), {len(sans)} sans mention dans l'étiquette" + (f" ({', '.join(sans[:3])})" if sans else ""))
    else:
        mis(71, "NA", "aucun champ obligatoire dans le HTML envoyé")
    fmt = [c for c in champs if c.get("type") in ("date", "tel") or c.get("pattern")]
    if fmt:
        sans = [c.get("name", "?") for c in fmt if not re.search(r"jj|mm|aaaa|format|ex\.|exemple|\d{2}[ ./-]\d{2}", etiquette(c), re.I)]
        mis(72, "NC" if sans else "C", f"{len(fmt)} champ(s) à format imposé, {len(sans)} sans format indiqué")
    else:
        mis(72, "NA", "aucun champ à format imposé (date, téléphone, motif) dans le HTML envoyé")
    lim = [c for c in champs if c.get("maxlength", "").isdigit() and int(c["maxlength"]) < 256]
    if lim:
        sans = [c.get("name", "?") for c in lim if not re.search(r"caract", etiquette(c), re.I)]
        mis(74, "NC" if sans else "C", f"{len(lim)} champ(s) limité(s) (maxlength), {len(sans)} sans limite indiquée")
    else:
        mis(74, "NA", "aucun champ limité en nombre de caractères")

    # 105 : coordonnées complètes accessibles (sur la page ou par un lien vers mentions légales ou contact)
    tel, cp = TEL.search(txt), re.search(r"\b\d{5}\b", txt)
    lien_coord = [a.get("href", "") for a, t in liens if re.search(r"mentions|legal|contact", a.get("href", "") + t, re.I)]
    mis(105, "C" if (tel and cp) or lien_coord else "NC", "adresse et téléphone dans la page" if tel and cp else f"lien vers {lien_coord[0][:60]}" if lien_coord else "ni coordonnées ni lien vers mentions légales ou contact")

    # 115 : référentiel déclaré
    ref = re.search(r"RGAA|WCAG|Opquast|déclaration d.accessibilit|accessibility statement", txt, re.I)
    mis(115, "C" if ref else "NA", f"référentiel cité : « {ref.group(0)} »" if ref else "aucun référentiel déclaré comme respecté")

    # 133, 134 : versions traduites
    alt = [(attrs(m.group(0)).get("hreflang", ""), attrs(m.group(0)).get("href", "")) for m in re.finditer(r"<link[^>]+hreflang[^>]*>", brut, re.I)]
    langues = {l.split("-")[0].lower() for l, _ in alt if l and l != "x-default"}
    if len(langues) < 2:
        mis(133, "NA", "site en une seule langue (aucune alternative hreflang)"); mis(134, "NA", "site en une seule langue")
    else:
        chemin = re.sub(r"^/[a-z]{2}(-[a-z]{2})?(?=/|$)", "", urlsplit(url).path, flags=re.I).rstrip("/")
        autres = [h for l, h in alt if l.split("-")[0].lower() != "fr" and l != "x-default"]
        bons = [h for h in autres if re.sub(r"^/[a-z]{2}(-[a-z]{2})?(?=/|$)", "", urlsplit(h).path, flags=re.I).rstrip("/") == chemin]
        mis(133, "C" if autres and len(bons) == len(autres) else "NC", f"{len(bons)} lien(s) hreflang sur {len(autres)} pointent vers la traduction de cette page")
        noms = {t.strip().lower() for a, t in liens if t.strip().lower() in ENDO | EXO_FR} | {texte(o).lower() for o in re.findall(r"<option[^>]*>(.*?)</option>", html, re.S | re.I) if texte(o).lower() in ENDO | EXO_FR}
        if noms:
            exo = noms & EXO_FR
            mis(134, "NC" if exo else "C", f"langues proposées : {', '.join(sorted(noms))[:120]}")
        else:
            mis(134, "NA", "sélecteur de langue sans nom de langue lisible dans le HTML envoyé (codes ou drapeaux)")

    # 142 : liens externes différenciés ; 144 : liens vers un logiciel externe explicites
    ext = [(a, t) for a, t in liens if a.get("href", "").startswith("http") and urlsplit(a["href"]).netloc not in (hote, "")]
    if ext:
        sig = [1 for a, t in ext if re.search(r"extern|nouvel|new|blank|ouvre|↗|icon", a.get("aria-label", "") + a.get("title", "") + a.get("class", "") + t, re.I)]
        mis(142, "C" if len(sig) == len(ext) else "NC", f"{len(ext)} lien(s) externe(s), {len(sig)} signalé(s) comme tels")
    else:
        mis(142, "NA", "aucun lien externe")
    logi = [(a, t) for a, t in liens if re.match(r"(mailto|tel|sms):", a.get("href", ""), re.I)]
    if logi:
        flous = [t for a, t in logi if not re.search(r"@|\d{2}|mail|courriel|écri|appel|téléphon|contact|sms", t + a.get("aria-label", "") + a.get("title", ""), re.I)]
        mis(144, "NC" if flous else "C", f"{len(logi)} lien(s) mailto/tel, {len(flous)} au libellé non explicite")
    else:
        mis(144, "NA", "aucun lien mailto, tel ou sms")

    # fichiers en téléchargement : 147, 150, 241
    fichiers = [(a, t) for a, t in liens if re.search(r"\.(pdf|docx?|xlsx?|pptx?|zip|odt)(\?|$)", a.get("href", ""), re.I)]
    if not fichiers:
        for n in (147, 150, 241):
            mis(n, "NA", "aucun fichier proposé en téléchargement sur la page")
    else:
        sans_fmt = [t for a, t in fichiers if not re.search(r"pdf|doc|xls|ppt|zip|odt", t, re.I)]
        mis(147, "NC" if sans_fmt else "C", f"{len(fichiers)} fichier(s), {len(sans_fmt)} sans format indiqué dans le libellé")
        obscurs = [a["href"].split("/")[-1].split("?")[0] for a, t in fichiers if re.fullmatch(r"[A-Za-z0-9_-]{0,3}[0-9a-f_-]{8,}\.\w+", a["href"].split("/")[-1].split("?")[0], re.I)]
        mis(150, "NC" if obscurs else "C", f"{len(fichiers)} fichier(s), {len(obscurs)} au nom illisible" + (f" (« {obscurs[0][:40]} »)" if obscurs else ""))

    # 152 : liens internes valides (échantillon de 6 liens différents par page, requêtes HEAD)
    internes = []
    for a, t in liens:
        h = a.get("href", "")
        if h.startswith(("#", "mailto:", "tel:", "javascript:")) or not h:
            continue
        u = urljoin(url, h)
        if urlsplit(u).netloc == hote and u not in internes and not re.search(r"/cart/|/account|logout|/checkout", u):
            internes.append(u)
    ech = internes[:: max(1, len(internes) // 6)][:6]
    casses = [(u, s) for u in ech for s in [statut_lien(u)] if s >= 400 and s != 429]
    if ech:
        mis(152, "NC" if casses else "C", f"{len(ech)} lien(s) interne(s) testé(s) sur {len(internes)}, {len(casses)} cassé(s)" + (f" : {casses[0][0][-50:]} ({casses[0][1]})" if casses else ""))

    # newsletter : 177, 178, 179
    nl = re.search(r"newsletter|lettre d.information|inscri\w+ (?:à|a) (?:notre|la) (?:newsletter|lettre)", txt, re.I)
    if nl:
        arch = [t for a, t in liens if re.search(r"archive|newsletters? pr[ée]c[ée]dentes?|anciennes? newsletters?", t + a.get("href", ""), re.I)]
        mis(177, "C" if arch else "NC", f"lien « {arch[0][:50]} »" if arch else "formulaire d'inscription sans lien vers la dernière newsletter")
        mis(178, "C" if arch else "NC", f"lien « {arch[0][:50]} »" if arch else "aucune archive des newsletters liée")
        zone = txt[max(0, nl.start() - 300): nl.end() + 400]
        freq = re.search(r"par (semaine|mois|jour)|hebdomadaire|mensuel|chaque (semaine|mois)|fois par|fréquence", zone, re.I)
        mis(179, "C" if freq else "NC", f"« {freq.group(0)} » près du formulaire" if freq else "aucune fréquence d'envoi annoncée près du formulaire d'inscription")
    else:
        for n in (177, 178, 179):
            mis(n, "NA", "aucune inscription à une newsletter sur la page")

    # feuilles de style : 141, 190, 191
    css = styles_inline
    for m in list(re.finditer(r"<link[^>]+rel=[\"']?stylesheet[^>]*>", brut, re.I))[:8]:
        h = attrs(m.group(0)).get("href", "")
        if not h:
            continue
        u = urljoin(url, h)
        if u not in css_cache:
            st, _, contenu = get(u)
            css_cache[u] = contenu if st == 200 else ""
        css += " " + css_cache[u]
    if css.strip():
        visited = re.findall(r"[^{}]*:visited[^{]*\{[^}]*(color|text-decoration|border|background)[^}]*\}", css, re.I)
        mis(141, "C" if visited else "NC", f"{len(visited)} règle(s) :visited qui changent l'apparence" if visited else "aucune règle :visited dans les feuilles de style")
        familles = re.findall(r"font-family\s*:\s*([^;}{]+)", css, re.I)
        sans_gen = [f.strip() for f in familles if not GEN.search(f) and not re.search(r"icon|awesome|glyph|swiper|slick", f, re.I)]
        mis(190, "NC" if sans_gen else "C", f"{len(familles)} déclaration(s) font-family, {len(sans_gen)} sans famille générique" + (f" (ex. « {sans_gen[0][:50]} »)" if sans_gen else ""))
        just = re.findall(r"text-align\s*:\s*justify", css, re.I)
        mis(191, "NC" if just else "C", f"{len(just)} déclaration(s) text-align: justify" if just else "aucun texte justifié dans les feuilles de style")
    return r


def main() -> int:
    global DELAI
    ap = argparse.ArgumentParser()
    ap.add_argument("--delai", type=float, default=6.0)
    DELAI = ap.parse_args().delai
    ecrans = list(csv.DictReader((RACINE / "scripts" / "ecrans_en_ligne.csv").open(encoding="utf-8")))
    sortie = RACINE / "resultats" / f"sources-{date.today():%Y-%m-%d}"
    sortie.mkdir(parents=True, exist_ok=True)
    f = sortie / "html2.json"
    res = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    css_cache: dict = {}
    for e in ecrans:
        s = res.setdefault(e["service"], {})
        if e["url"] in s and "_non_teste" not in s[e["url"]]:
            continue
        st, finale, html = get(e["url"])
        if st != 200 or not html:
            s[e["url"]] = {"_gabarit": e["gabarit"], "_non_teste": f"code {st}"}
        elif urlsplit(finale).netloc != urlsplit(e["url"]).netloc:
            s[e["url"]] = {"_gabarit": e["gabarit"], "_non_teste": "quitte le site (compte client hébergé par Shopify)"}
        elif re.search(r"cf-challenge|captcha|Just a moment|connexion doit être vérifiée", html[:6000], re.I):
            s[e["url"]] = {"_gabarit": e["gabarit"], "_non_teste": "vérification anti-robot : non contournée"}
        else:
            s[e["url"]] = {"_gabarit": e["gabarit"], **regles(e["url"], e["gabarit"], html, css_cache)}
        f.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(e["service"], "|", e["gabarit"], "|", s[e["url"]].get("_non_teste") or " ".join(f"{k}:{v[0]}" for k, v in s[e["url"]].items() if not k.startswith("_")), flush=True)
    print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
