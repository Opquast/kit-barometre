#!/usr/bin/env python3
"""Deuxième source « HTML brut, sans JavaScript » pour les règles mesurées par scripts/controles_page.js.

controles_page.js lit le DOM rendu dans Chromium, après exécution des scripts. Ce script-ci lit le code HTML tel que
le serveur l'envoie (requête GET, aucun JavaScript), avec un autre analyseur (html.parser de Python). Les deux
lectures peuvent diverger quand le thème injecte ou retire des éléments en JavaScript : c'est justement ce que le
recoupement doit faire apparaître. Indépendance partielle (même auteur, autre entrée, autre code) : à présenter
comme telle.

Règles : 13, 15, 28, 46, 92, 95, 97, 98, 102, 107, 116, 120, 122, 128, 145, 146, 155, 164, 169, 170, 237, 238, 242, 243.

Usage : python3 scripts/sources_html.py [--delai 8]
Sortie : resultats/sources-AAAA-MM-JJ/html.json  { site: { url: { regle: [statut, preuve, "HTML brut (sans JavaScript)"] } } }
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

RACINE = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
OUTIL = "HTML brut (sans JavaScript)"
TEL = re.compile(r"(?<![\d/=.-])(?:\+33\s?|0)[1-9](?:[\s.-]?\d{2}){4}(?!\d)")


class Analyse(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.liens, self.inputs, self.imgs, self.objets, self.videos, self.tables, self.boutons, self.forms = [], [], [], [], [], [], [], []
        self.title, self._dans_title, self._lien = "", False, None
        self.body_attrs, self.texte, self._pile_table = {}, [], []
        self.ordre_liens = 0
        self._ignore = 0  # contenu de <script>, <style>, <template>, <noscript> : pas affiché tel quel (correctif du 12/11)

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag in ("script", "style", "template", "noscript"):
            self._ignore += 1
            return
        if self._ignore:
            return
        if tag == "a":
            self._lien = {"href": a.get("href", ""), "target": a.get("target", ""), "titre": a.get("title", ""), "aria": a.get("aria-label", ""), "texte": "", "rang": self.ordre_liens}
            self.ordre_liens += 1
            self.liens.append(self._lien)
        elif tag == "input":
            self.inputs.append(a)
        elif tag == "img":
            self.imgs.append(a)
        elif tag in ("object", "embed", "iframe"):
            self.objets.append((tag, a))
        elif tag == "video":
            self.videos.append({"attrs": a, "pistes": 0})
        elif tag == "track" and self.videos:
            self.videos[-1]["pistes"] += 1
        elif tag == "table":
            t = {"th": 0, "caption": False, "role": a.get("role", "")}
            self.tables.append(t); self._pile_table.append(t)
        elif tag == "th" and self._pile_table:
            self._pile_table[-1]["th"] += 1
        elif tag == "caption" and self._pile_table:
            self._pile_table[-1]["caption"] = True
        elif tag == "button":
            self.boutons.append(a)
        elif tag == "form":
            self.forms.append(a)
        elif tag == "body":
            self.body_attrs = a
        elif tag == "title":
            self._dans_title = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "template", "noscript"):
            self._ignore = max(0, self._ignore - 1)
            return
        if tag == "a":
            self._lien = None
        elif tag == "title":
            self._dans_title = False
        elif tag == "table" and self._pile_table:
            self._pile_table.pop()

    def handle_data(self, data):
        if self._ignore:
            return
        if self._dans_title:
            self.title += data
        if self._lien is not None:
            self._lien["texte"] += data
        self.texte.append(data)


def get(url: str, delai: float) -> tuple[int, str, str]:
    time.sleep(delai)
    for essai in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"}), timeout=30) as r:
                return r.status, r.geturl(), r.read().decode("utf-8", "replace")
        except HTTPError as e:
            if e.code == 429 and essai < 2:
                time.sleep(30 * (essai + 1)); continue
            return e.code, url, ""
        except (URLError, TimeoutError, OSError) as e:
            return 0, url, str(e)
    return 429, url, ""


def regles(url: str, gabarit: str, html: str, nom_site: str) -> dict:
    a = Analyse(); a.feed(html)
    txt = re.sub(r"\s+", " ", " ".join(a.texte))
    r: dict = {}
    hrefs = [l["href"] for l in a.liens]
    def mis(n, st, preuve): r[str(n)] = [st, TEL.sub("[téléphone masqué]", preuve), OUTIL]  # aucun numéro dans les résultats
    conf = [h for h in hrefs if re.search(r"privacy|confidentialit|donnees-personnelles|vie-privee", h, re.I)]
    mis(15, "C" if conf else "NC", f"lien vers la politique de confidentialité : {conf[0][:80]}" if conf else "aucun lien vers la politique de confidentialité dans le HTML envoyé")
    cgv = [h for h in hrefs if re.search(r"terms|cgv|conditions-generales|cgu|conditions-de-vente|terms-of-sale", h, re.I)]
    mis(46, "C" if cgv else "NC", f"lien vers les conditions : {cgv[0][:80]}" if cgv else "aucun lien vers les conditions de vente ou d'utilisation dans le HTML envoyé")
    t = re.sub(r"\s+", " ", a.title).strip()
    mots = [m for m in re.findall(r"[A-Za-zÀ-ÿ']{4,}", nom_site) if m.lower() not in ("filatures",)]
    mis(102, "C" if any(m.lower() in t.lower() for m in mots) else "NC", f"titre « {t[:90]} »")
    accueil = [l for l in a.liens if re.fullmatch(r"(https?://[^/]+)?/([a-z]{2}/?)?", l["href"] or "x")]
    mis(155, "C" if accueil else "NC", f"{len(accueil)} lien(s) vers l'accueil" if accueil else "aucun lien vers l'accueil dans le HTML envoyé")
    evit = [l for l in a.liens[:8] if l["href"].startswith("#") and len(l["href"]) > 1]
    mis(164, "C" if evit else "NC", f"lien d'accès rapide en tête du code : {evit[0]['href']} « {evit[0]['texte'].strip()[:40]} »" if evit else "aucun lien d'ancre parmi les 8 premiers liens du code")
    tels = TEL.findall(txt)
    tel_liens = [h for h in hrefs if h.startswith("tel:")]
    if tels or tel_liens:
        mis(145, "C" if tel_liens else "NC", f"{len(set(tels))} numéro(s) dans le texte, {len(tel_liens)} lien(s) tel:")
        sans_indicatif = [x for x in set(tels) if not x.startswith("+")] + [h for h in tel_liens if not h[4:].strip().startswith("+")]
        mis(128, "NC" if sans_indicatif else "C", f"{len(sans_indicatif)} numéro(s) sans indicatif international" + (f" : {sans_indicatif[0]}" if sans_indicatif else ""))
    else:
        mis(145, "NA", "aucun numéro de téléphone dans le HTML envoyé"); mis(128, "NA", "aucun numéro de téléphone dans le HTML envoyé")
    moyens = {"e-mail" for h in hrefs if h.startswith("mailto:")} | {"téléphone" for h in tel_liens} | {"formulaire ou page contact" for h in hrefs if re.search(r"/contact|/pages/nous-contacter", h, re.I)}
    mis(107, "C" if len(moyens) >= 2 else "NC", f"moyens de contact liés depuis la page : {', '.join(sorted(moyens)) or 'aucun'}")
    blank = [l for l in a.liens if l["target"] == "_blank"]
    averti = [l for l in blank if re.search(r"nouvel(le)? (fenêtre|onglet)|new (window|tab)|s'ouvre", l["titre"] + l["aria"] + l["texte"], re.I)]
    mis(146, "NA" if not blank else "C" if len(averti) == len(blank) else "NC", f"{len(blank)} lien(s) en nouvelle fenêtre, {len(averti)} avec avertissement")
    champs = [i for i in a.inputs if i.get("type", "text") not in ("hidden", "submit", "button", "checkbox", "radio", "image", "reset")]
    if champs:
        mal_types = [i.get("name", "") for i in champs if i.get("type", "text") == "text" and re.search(r"mail|phone|tel|search|^q$|date", i.get("name", "") + i.get("id", ""), re.I)]
        mis(95, "NC" if mal_types else "C", f"{len(champs)} champ(s) ; type « text » pour : {', '.join(mal_types[:4])}" if mal_types else f"{len(champs)} champ(s), types adaptés")
        perso = [i for i in champs if re.search(r"mail|name|nom|prenom|phone|tel|address|adresse|zip|postal|city|ville", i.get("name", "") + i.get("id", ""), re.I) and i.get("type") != "search"]
        if perso:
            sans = [i.get("name", "") for i in perso if not i.get("autocomplete")]
            mis(97, "NC" if sans else "C", f"{len(perso)} champ(s) personnels, {len(sans)} sans attribut autocomplete" + (f" ({', '.join(sans[:3])})" if sans else ""))
        else:
            mis(97, "NA", "aucun champ de donnée personnelle dans le HTML envoyé")
        bloque = [i.get("name", "") for i in champs if re.search(r"return\s+false|preventDefault", i.get("onpaste", ""))]
        mis(92, "NC" if bloque else "C", f"copier-coller bloqué sur : {', '.join(bloque)}" if bloque else f"{len(champs)} champ(s), aucun onpaste bloquant")
    else:
        for n in (95, 97, 92):
            mis(n, "NA", "aucun champ de saisie dans le HTML envoyé")
    sensibles = [h for h in hrefs if re.search(r"[?&](password|pwd|token|email|mail)=", h, re.I)] + [f.get("action", "") for f in a.forms if f.get("method", "get").lower() == "get" and re.search(r"login|account|password", f.get("action", ""), re.I)]
    mis(28, "NC" if sensibles else "C", f"donnée sensible dans une adresse : {sensibles[0][:80]}" if sensibles else "aucune donnée sensible dans les adresses des liens et formulaires GET")
    desact = [b for b in a.boutons if "disabled" in b]
    masques = [b for b in desact if b.get("aria-hidden") == "true"]
    mis(98, "NA" if not desact else "NC" if masques else "C", f"{len(desact)} bouton(s) désactivé(s), {len(masques)} masqué(s) aux lecteurs d'écran")
    deco = [i for i in a.imgs if i.get("alt") == "" or i.get("role") == "presentation"]
    sans_alt = [i for i in a.imgs if "alt" not in i]
    mis(116, "NA" if not a.imgs else "NC" if sans_alt else "C", f"{len(a.imgs)} image(s) : {len(deco)} à alternative vide, {len(sans_alt)} sans attribut alt")
    obj = [(t_, x) for t_, x in a.objets if t_ != "iframe" or x.get("src", "").strip()]
    sans_titre = [t_ for t_, x in obj if not (x.get("title") or x.get("aria-label") or x.get("alt"))]
    mis(120, "NA" if not obj else "NC" if sans_titre else "C", f"{len(obj)} objet(s) inclus (iframe, object, embed), {len(sans_titre)} sans alternative (title)")
    mis(122, "NA" if not a.videos else "C" if all(v["pistes"] for v in a.videos) else "NC", f"{len(a.videos)} vidéo(s), {sum(1 for v in a.videos if v['pistes'])} avec piste de sous-titres")
    copie = re.search(r"oncopy|oncontextmenu|user-select\s*:\s*none", " ".join(f"{k}={v}" for k, v in a.body_attrs.items()), re.I) or re.search(r"<body[^>]+(oncopy|onselectstart)", html, re.I)
    mis(237, "NC" if copie else "C", "copie bloquée sur <body>" if copie else "aucun blocage de la copie sur <body>")
    menu = re.search(r"<body[^>]+oncontextmenu|document\.oncontextmenu\s*=|addEventListener\(\s*['\"]contextmenu['\"][^)]*preventDefault", html, re.I)
    mis(238, "NC" if menu else "C", "menu contextuel bloqué" if menu else "aucun blocage du menu contextuel dans le HTML envoyé")
    donnees = [t_ for t_ in a.tables if t_["role"] not in ("presentation", "none")]
    if donnees:
        mis(242, "C" if all(t_["th"] for t_ in donnees) else "NC", f"{len(donnees)} tableau(x) de données, {sum(1 for t_ in donnees if t_['th'])} avec en-têtes th")
        mis(243, "C" if all(t_["caption"] for t_ in donnees) else "NC", f"{len(donnees)} tableau(x) de données, {sum(1 for t_ in donnees if t_['caption'])} avec titre (caption)")
    else:
        mis(242, "NA", "aucun tableau de données"); mis(243, "NA", "aucun tableau de données")
    if gabarit == "Recherche":
        mis(169, "C", f"résultats atteints par une adresse web : {url}")
        mis(170, "C" if any(i.get("type") == "search" or i.get("name") == "q" for i in a.inputs) else "NC", "champ de recherche présent sur la page de résultats" if any(i.get("name") == "q" for i in a.inputs) else "aucun champ de recherche dans le HTML envoyé de la page de résultats")
        nb = re.search(r"\b\d+\s+(résultats?|produits?|articles?)\b", txt, re.I)
        mis(13, "C" if nb else "NC", f"« {nb.group(0)} »" if nb else "aucun nombre de résultats dans le HTML envoyé (peut être ajouté en JavaScript)")
    else:
        for n in (13, 169, 170):
            mis(n, "NA", "pas une page de résultats de recherche")
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--delai", type=float, default=8.0)
    a = ap.parse_args()
    ecrans = list(csv.DictReader((RACINE / "scripts" / "ecrans_en_ligne.csv").open(encoding="utf-8")))
    sortie = RACINE / "resultats" / f"sources-{date.today():%Y-%m-%d}"
    sortie.mkdir(parents=True, exist_ok=True)
    f = sortie / "html.json"
    res = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    for e in ecrans:
        s = res.setdefault(e["service"], {})
        if e["url"] in s and "_non_teste" not in s[e["url"]]:
            continue
        st, finale, html = get(e["url"], a.delai)
        if st != 200 or not html:
            s[e["url"]] = {"_gabarit": e["gabarit"], "_non_teste": f"code {st}"}
        elif re.match(r"https?://([^/]+)", finale).group(1) != re.match(r"https?://([^/]+)", e["url"]).group(1):
            s[e["url"]] = {"_gabarit": e["gabarit"], "_non_teste": "quitte le site (compte client hébergé par Shopify)"}
        elif re.search(r"cf-challenge|captcha|Just a moment", html[:5000], re.I):
            s[e["url"]] = {"_gabarit": e["gabarit"], "_non_teste": "vérification anti-robot : non contournée"}
        else:
            s[e["url"]] = {"_gabarit": e["gabarit"], **regles(e["url"], e["gabarit"], html, e["service"])}
        f.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(e["service"], "|", e["gabarit"], "|", s[e["url"]].get("_non_teste") or " ".join(f"{k}:{v[0]}" for k, v in s[e["url"]].items() if not k.startswith("_")), flush=True)
    print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
