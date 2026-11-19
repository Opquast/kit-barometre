#!/usr/bin/env python3
"""Régénère le corps de schema-parc.html (schéma et tableau du parc) en gardant ses styles.

Usage : python3 scripts/generer_schema.py
"""
from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from urllib.parse import urlsplit

import parc

RACINE = Path(__file__).resolve().parent.parent
PAGE = RACINE / "schema-parc.html"

OUTILS = [
    ("Script de contrôles réseau", "scripts/controles_reseau.py", "règles réseau · déterministe"),
    ("Claude Code + MCP Opquast", "navigateur intégré", "audit assisté par IA"),
    ("eServices Manager", "esm.opquast.com · robot Opquast", "inventaire, robot, baromètre"),
    ("Dépôt Git", "dépôt du kit", "versions et preuves"),
]


def sites() -> list[tuple[str, str, str, int]]:
    """(nom, adresse de l'accueil, description, nombre d'écrans) de chaque site du parc, adresse tirée du CSV des écrans."""
    ecrans = list(csv.DictReader((RACINE / "scripts" / "ecrans_en_ligne.csv").open(encoding="utf-8")))
    out = []
    for s in parc.sites():
        ec = [x for x in ecrans if x["service"] == s["nom"]]
        accueil = next((x["url"] for x in ec if x["gabarit"].startswith("Accueil")), ec[0]["url"] if ec else "")
        u = urlsplit(accueil)
        out.append((s["nom"], (u.netloc + u.path).rstrip("/"), s.get("description", ""), len(ec)))
    return out


def comptes_email() -> list[tuple[str, str, str]]:
    """(compte, accès, classe) : « lu » si le dernier état consolidé contient ses e-mails, sinon « à connecter »."""
    etats = sorted((RACINE / "resultats").glob("etat-*/etat.json"))
    lus = json.loads(etats[-1].read_text(encoding="utf-8")).get("emails", {}) if etats else {}
    return [(c, "lecture seule", "ok") if c in lus else (c, "accès à ouvrir", "warn") for c in parc.comptes_email().values()]


def e(t: str) -> str:
    return html.escape(t, quote=True)


def bilans() -> dict:
    out = {}
    for f in sorted((RACINE / "resultats").glob("reseau-*/resultats.json")):
        for nom, v in json.loads(f.read_text(encoding="utf-8"))["services"].items():
            nc = {r["rule_number"] for r in v["site"] if r["status"] == "non-conforme"}
            nc |= {c["rule_number"] for p in v["pages"] for c in p["controles"] if c["status"] == "non-conforme"}
            out[nom] = len(nc)
    return out


def chip(xr, y, w, label, cls):
    x = xr - w
    return (f'<rect x="{x:.1f}" y="{y}" width="{w}" height="20" rx="10" class="chip-{cls}"/>'
            f'<text x="{x + w / 2:.1f}" y="{y + 14}" class="chiptxt-{cls}" text-anchor="middle">{e(label)}</text>')


def card(x, y, w, h, stripe, nom, chemin, note, chips):
    o = [f'<g class="card"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" class="card-bg"/>',
         f'<rect x="{x}" y="{y + 10}" width="4" height="{h - 20}" rx="2" class="stripe-{stripe}"/>',
         f'<text x="{x + 16}" y="{y + 24}" class="cname">{e(nom)}</text>',
         f'<text x="{x + 16}" y="{y + 44}" class="cpath">{e(chemin)}</text>']
    if note:
        o.append(f'<text x="{x + 16}" y="{y + 62}" class="cnote">{e(note)}</text>')
    xr = x + w - 14
    for label, wch, cls in chips:
        o.append(chip(xr, y + h - 30, wch, label, cls))
        xr -= wch + 6
    o.append('</g>')
    return "\n".join(o)


def main() -> None:
    page = PAGE.read_text(encoding="utf-8")
    tete = page[:page.index('<div class="wrap">')]
    b = bilans()
    qui = parc.responsable()
    ss, emails = sites(), comptes_email()
    nb_ecrans = {n for *_, n in ss}
    gabarits = f"{nb_ecrans.pop()} gabarits chacun" if len(nb_ecrans) == 1 else "gabarits du CSV des écrans"
    rangs = max(1, (len(ss) + 1) // 2)
    h_sites = 20 + rangs * 88
    y_crm = 92 + h_sites + 12
    h_crm = (32 + ((len(emails) + 1) // 2) * 88) if emails else 0
    h = max(608, y_crm + h_crm + 40 - 16)
    svg = [f'<svg viewBox="0 0 1160 {h + 32}" role="img" aria-labelledby="svgt svgd" xmlns="http://www.w3.org/2000/svg">',
           f'<title id="svgt">Schéma du parc Opquast de {e(qui)}</title>',
           f'<desc id="svgd">À gauche, en ligne : {len(ss)} site(s) du parc et {len(emails)} compte(s) e-mail. '
           'À droite, les outils de mesure : script de contrôles réseau, Claude Code avec le MCP Opquast, eServices Manager et le dépôt Git.</desc>',
           '<defs><marker id="tip" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="tip"/></marker></defs>',
           f'<rect x="16" y="16" width="760" height="{h}" rx="16" class="zone-web"/>',
           f'<rect x="800" y="16" width="344" height="{h}" rx="16" class="zone-mac"/>',
           '<text x="36" y="50" class="zone-title">En ligne</text>',
           '<text x="36" y="70" class="zone-sub">sites en production · audit en lecture seule, aucune commande</text>',
           '<text x="820" y="50" class="zone-title">Outils de mesure</text>',
           '<text x="820" y="70" class="zone-sub">trois couches : automatique, IA, humaine</text>',
           f'<rect x="30" y="92" width="732" height="{h_sites}" rx="11" class="group group-shop"/>',
           f'<text x="44" y="112" class="glabel">Sites du parc · {e(gabarits)}</text>']
    for i, (nom, url, desc, _) in enumerate(ss):
        x, y = 42 + (i % 2) * 360, 122 + (i // 2) * 88
        if nom in b:
            chips = [(f"{b[nom]} non conf. réseau", 128, "warn" if b[nom] else "ok")]
        else:
            chips = [("réseau en cours", 108, "dep")]
        svg.append(card(x, y, 348, 80, "shop", nom, url, desc, chips))
    if emails:
        svg += [f'<rect x="30" y="{y_crm}" width="732" height="{h_crm}" rx="11" class="group group-crm"/>',
                f'<text x="44" y="{y_crm + 20}" class="glabel">Comptes e-mail · e-mails et formulaires</text>']
        for i, (nom, acces, cls) in enumerate(emails):
            svg.append(card(42 + (i % 2) * 360, y_crm + 30 + (i // 2) * 88, 348, 80, "crm", nom, "socle + Newsletter", "",
                            [(acces, 104 if cls == "warn" else 92, cls if cls == "warn" else "dep")]))
    for i, (nom, chemin, note) in enumerate(OUTILS):
        svg.append(card(816, 92 + i * 128, 312, 112, "local" if i < 3 else "svc", nom, chemin, note, []))
    svg += ['<path d="M816 148 H766" class="link" marker-end="url(#tip)"/>',
            '<path d="M816 276 H766" class="link" marker-end="url(#tip)"/>',
            '<text x="791" y="140" class="linklabel" text-anchor="middle">mesure</text>',
            '</svg>']

    lignes = []
    for nom, url, desc, n in ss:
        etat = (f'<span class="pill pill-{"warn" if b[nom] else "ok"}">{b[nom]} non conforme(s) en réseau</span>' if nom in b
                else '<span class="pill pill-warn">Contrôles réseau en cours</span>')
        lignes.append(f'<tr><td class="id id-shop">Site</td><td><strong>{e(nom)}</strong><span class="cat">{e(desc)}</span></td>'
                      f'<td class="mono">{e(url)}</td><td>{n}</td><td>{etat}</td></tr>')
    for nom, acces, cls in emails:
        etat = f'<span class="pill pill-{"ok" if cls == "ok" else "warn"}">{"Lecture OK" if cls == "ok" else "Accès à ouvrir"}</span>'
        lignes.append(f'<tr><td class="id id-crm">E-mail</td><td><strong>{e(nom)}</strong><span class="cat">e-mails et formulaires</span></td>'
                      f'<td class="mono">compte e-mail ({e(acces)})</td><td>-</td><td>{etat}</td></tr>')
    a_ouvrir = [nom for nom, _, cls in emails if cls == "warn"]
    note_email = (f'\n      <li><strong>Comptes e-mail à connecter</strong>{e(", ".join(a_ouvrir))} : e-mails non lus tant que l\'accès n\'est pas ouvert.</li>'
                  if a_ouvrir else "")
    total = len(ss) + len(emails)

    corps = f'''<div class="wrap">
  <header>
    <div class="eyebrow-h">Baromètre qualité Opquast</div>
    <h1>Parc Opquast de {e(qui)}</h1>
    <p class="lede">Les {total} services du parc (referentiel/parc.json) : {len(ss)} site(s) et {len(emails)} compte(s) e-mail, avec les outils qui les mesurent.</p>
    <ul class="counts">
      <li><span class="dot" style="background:var(--shop)"></span><b>{len(ss)}</b>sites du parc</li>
      <li><span class="dot" style="background:var(--crm)"></span><b>{len(emails)}</b>comptes e-mail</li>
      <li><span class="dot" style="background:var(--local)"></span><b>{sum(n for *_, n in ss)}</b>écrans de sites à auditer</li>
    </ul>
  </header>

  <figure>
    <div class="scroll">
{chr(10).join(svg)}
    </div>
  </figure>

  <section>
    <h2>Les {total} services</h2>
    <div class="tbl"><table>
      <thead><tr><th>Catégorie</th><th>Service</th><th>Adresse ou accès</th><th>Écrans</th><th>État</th></tr></thead>
      <tbody>
{chr(10).join(lignes)}
      </tbody>
    </table></div>
  </section>

  <section>
    <h2>À savoir</h2>
    <ul class="notes">
      <li><strong>Lecture seule</strong>Aucune commande passée sur les sites, rien n'est modifié dans les comptes e-mail, aucune donnée client dans les rapports.</li>
      <li><strong>Pages bloquées</strong>Le script s'arrête au code 429 et note la page « non testée » ; elle est vérifiée dans le navigateur.</li>
      <li><strong>Mêmes gabarits partout</strong>Les sites sont mesurés sur les mêmes gabarits (scripts/ecrans_en_ligne.csv) : ils se comparent directement.</li>{note_email}
    </ul>
  </section>

  <footer>Sources : referentiel/parc.json, scripts/ecrans_en_ligne.csv, résultats des contrôles réseau · page générée par scripts/generer_schema.py</footer>
</div>
'''
    PAGE.write_text(tete + corps, encoding="utf-8")
    print("schema-parc.html régénéré")


if __name__ == "__main__":
    main()
