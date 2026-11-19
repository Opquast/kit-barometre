#!/usr/bin/env python3
"""Régénère le corps de schema-parc.html (schéma et tableau du parc) en gardant ses styles.

Usage : python3 scripts/generer_schema.py
"""
from __future__ import annotations

import html
import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
PAGE = RACINE / "schema-parc.html"

SITES = [
    ("Boutique A", "boutique-a.example", "confitures, biscuits"),
    ("Boutique B", "boutique-b.example", "mode homme et femme"),
    ("Boutique C", "boutique-c.example", "soins capillaires"),
    ("Boutique D", "boutique-d.example/fr", "mode homme"),
    ("Boutique E", "boutique-e.example", "arts de la table"),
    ("Boutique F", "boutique-f.example", "tee-shirts, 4 langues"),
]
KLAVIYO = [("Boutique C", "lecture seule", "ok"), ("Boutique F", "accès à ouvrir", "warn")]
OUTILS = [
    ("Script de contrôles réseau", "scripts/controles_reseau.py", "19 règles · déterministe"),
    ("Claude Code + MCP Opquast", "Claude Opus 5.5 · navigateur intégré", "audit assisté par IA"),
    ("eServices Manager", "esm.opquast.com · robot Opquast", "inventaire, robot, baromètre"),
    ("Dépôt Git privé", "github.com/itsmatlsr/opquast-barometre", "versions et preuves"),
]


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
    svg = ['<svg viewBox="0 0 1160 640" role="img" aria-labelledby="svgt svgd" xmlns="http://www.w3.org/2000/svg">',
           '<title id="svgt">Schéma du parc Opquast de Mattea</title>',
           '<desc id="svgd">À gauche, en ligne : six sites e-commerce clients sur Shopify et deux comptes Klaviyo. '
           'À droite, les outils de mesure : script de contrôles réseau, Claude Code avec le MCP Opquast, eServices Manager et le dépôt Git.</desc>',
           '<defs><marker id="tip" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="tip"/></marker></defs>',
           '<rect x="16" y="16" width="760" height="608" rx="16" class="zone-web"/>',
           '<rect x="800" y="16" width="344" height="608" rx="16" class="zone-mac"/>',
           '<text x="36" y="50" class="zone-title">En ligne, chez les clients</text>',
           '<text x="36" y="70" class="zone-sub">sites en production · audit en lecture seule, aucune commande</text>',
           '<text x="820" y="50" class="zone-title">Outils de mesure</text>',
           '<text x="820" y="70" class="zone-sub">trois couches : automatique, IA, humaine</text>',
           '<rect x="30" y="92" width="732" height="300" rx="11" class="group group-shop"/>',
           '<text x="44" y="112" class="glabel">Sites e-commerce clients · Shopify · 8 gabarits chacun</text>']
    for i, (nom, url, secteur) in enumerate(SITES):
        x, y = 42 + (i % 2) * 360, 122 + (i // 2) * 88
        if nom in b:
            chips = [(f"{b[nom]} non conf. réseau", 128, "warn" if b[nom] else "ok")]
        else:
            chips = [("réseau en cours", 108, "dep")]
        svg.append(card(x, y, 348, 80, "shop", nom, url, secteur, chips))
    svg += ['<rect x="30" y="404" width="732" height="122" rx="11" class="group group-crm"/>',
            '<text x="44" y="424" class="glabel">Klaviyo · comptes clients · e-mails et formulaires</text>']
    for i, (nom, acces, cls) in enumerate(KLAVIYO):
        svg.append(card(42 + i * 360, 434, 348, 80, "crm", f"Klaviyo {nom}", "6 écrans · socle + Newsletter", "",
                        [(acces, 104 if cls == "warn" else 92, cls if cls == "warn" else "dep")]))
    svg.append('<text x="44" y="560" class="cnote">Boutique C et Boutique F : site et CRM du même client, audités tous les deux.</text>')
    for i, (nom, chemin, note) in enumerate(OUTILS):
        svg.append(card(816, 92 + i * 128, 312, 112, "local" if i < 3 else "svc", nom, chemin, note, []))
    svg += ['<path d="M816 148 H766" class="link" marker-end="url(#tip)"/>',
            '<path d="M816 276 H766" class="link" marker-end="url(#tip)"/>',
            '<text x="791" y="140" class="linklabel" text-anchor="middle">mesure</text>',
            '</svg>']

    lignes = []
    for nom, url, secteur in SITES:
        etat = (f'<span class="pill pill-{"warn" if b[nom] else "ok"}">{b[nom]} non conforme(s) en réseau</span>' if nom in b
                else '<span class="pill pill-warn">Contrôles réseau en cours</span>')
        lignes.append(f'<tr><td class="id id-shop">E-commerce</td><td><strong>{e(nom)}</strong><span class="cat">{e(secteur)}</span></td>'
                      f'<td class="mono">{e(url)}</td><td>8</td><td>{etat}</td></tr>')
    for nom, acces, cls in KLAVIYO:
        etat = f'<span class="pill pill-{"ok" if cls == "ok" else "warn"}">{"Lecture OK" if cls == "ok" else "Accès à ouvrir"}</span>'
        lignes.append(f'<tr><td class="id id-crm">CRM</td><td><strong>Klaviyo {e(nom)}</strong><span class="cat">e-mails et formulaires</span></td>'
                      f'<td class="mono">connecteur Klaviyo ({e(acces)})</td><td>6</td><td>{etat}</td></tr>')

    corps = f'''<div class="wrap">
  <header>
    <div class="eyebrow-h">Formation Opquast · Expert qualité et conformité à l'ère de l'IA</div>
    <h1>Parc Opquast de Mattea</h1>
    <p class="lede">Les 8 services du périmètre de la note de cadrage (version 4 du 12 novembre 2026) : six sites e-commerce clients réalisés par Colorz sur Shopify et deux comptes Klaviyo, avec les outils qui les mesurent.</p>
    <ul class="counts">
      <li><span class="dot" style="background:var(--shop)"></span><b>6</b>sites e-commerce clients</li>
      <li><span class="dot" style="background:var(--crm)"></span><b>2</b>comptes Klaviyo</li>
      <li><span class="dot" style="background:var(--local)"></span><b>60</b>écrans à auditer</li>
    </ul>
  </header>

  <figure>
    <div class="scroll">
{chr(10).join(svg)}
    </div>
  </figure>

  <section>
    <h2>Les 8 services</h2>
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
      <li><strong>Lecture seule</strong>Aucune commande passée sur les sites, rien n'est modifié dans Klaviyo, aucune donnée client dans les rapports.</li>
      <li><strong>Pages bloquées par Shopify</strong>Le script s'arrête au code 429 et note la page « non testée » ; elle est vérifiée dans le navigateur.</li>
      <li><strong>Mêmes gabarits partout</strong>Accueil, collection, produit, panier, recherche, compte, page de contenu, page propre au site : les sites se comparent directement.</li>
      <li><strong>Klaviyo Boutique F</strong>Le connecteur actuel ne voit que le compte des Secrets de Boutique C : accès à ouvrir.</li>
    </ul>
  </section>

  <footer>Sources : note de cadrage v4, tests du 05/11 et du 12/11/2026, résultats des contrôles réseau · page générée par scripts/generer_schema.py</footer>
</div>
'''
    PAGE.write_text(tete + corps, encoding="utf-8")
    print("schema-parc.html régénéré")


if __name__ == "__main__":
    main()
