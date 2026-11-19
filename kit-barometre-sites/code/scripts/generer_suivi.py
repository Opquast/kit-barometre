#!/usr/bin/env python3
"""Ajoute à suivi-barometre.html un onglet par service du parc, avec tous ses tests.

Les onglets viennent du parc (referentiel/parc.json : un onglet par site, un par compte e-mail) et des écrans
(scripts/ecrans_en_ligne.csv). Sources : resultats/ (contrôles réseau, état consolidé, lectures…). Le contenu propre
à une mission (historique des tests d'accès, listes Fait et À faire, liens, scores basics relevés, jalons) est
optionnel : referentiel/suivi-complements.json (voir charger_complements). Relancer après chaque nouveau test, puis
republier la page à la même adresse.

Usage : python3 scripts/generer_suivi.py
"""
from __future__ import annotations

import html
import json
from datetime import date
import re
from pathlib import Path

import parc

RACINE = Path(__file__).resolve().parent.parent
PAGE = RACINE / "suivi-barometre.html"
RESEAU_DIR = RACINE / "resultats"

REGLES = {
    197: "HTTPS sur toutes les pages", 198: "Certificat signé et valide", 199: "En-tête HSTS",
    200: "Aucune ressource en HTTP", 206: "Détection MIME désactivée (nosniff)", 207: "Type MIME indiqué",
    210: "Protection XSS (X-XSS-Protection)", 211: "Intégration en cadre restreinte", 212: "CSP qui restreint l'origine",
    213: "Aucune version de logiciel annoncée", 214: "Intégrité des ressources tierces (SRI)",
    217: "Domaine de messagerie authentifié", 218: "Fonctionne avec et sans www", 219: "robots.txt",
    220: "Sitemap", 222: "Code 404 pour une adresse inexistante", 226: "Compression", 227: "En-têtes de cache",
    228: "Jeu de caractères dans l'en-tête",
}

# Statut -> (classe de pastille, libellé court)
PASTILLE = {
    "conforme": ("p-done", "conforme"), "non-conforme": ("p-block", "non conforme"),
    "non-applicable": ("p-na", "non applicable"), "non-testé": ("p-na", "non testé"),
    "indéterminé": ("p-todo", "indéterminé"), "ok": ("p-done", "OK"), "ko": ("p-block", "échec"),
    "attention": ("p-todo", "à surveiller"), "afaire": ("p-todo", "à faire"), "info": ("p-na", "info"),
}

# Onglets de service, construits par construire_services() depuis le parc (rempli par main()).
SERVICES: list[dict] = []
COMPLEMENTS: dict = {}
SUFFIXES_EMAIL = [("POPUP", "Popup"), ("FOOTER", "Pied de page"), ("BIENVENUE", "Bienvenue"), ("PANIER", "Panier"),
                  ("POSTACHAT", "Post-achat"), ("CAMPAGNE", "Campagne")]


def qui() -> str:
    """Personne responsable du baromètre (referentiel/parc.json)."""
    return parc.responsable()


def source_ce() -> str:
    """Nom de la source « contre-examen » dans la lecture critique (même construction que scripts/lecture_critique.py)."""
    return f"Contre-examen (validé par {qui()})"


def ident(nom: str) -> str:
    """Identifiant d'onglet : minuscules, sans accents ni espaces."""
    import unicodedata
    t = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-") or "service"


def charger_complements(chemin: Path | None = None) -> dict:
    """Compléments optionnels propres à une mission (referentiel/suivi-complements.json), vides sans le fichier.

    Clés : services ({nom: {desc, version, regles, ecrans, tests, afaire}}, remplace les valeurs génériques),
    fait et a_faire ([[groupe, [[titre, détail], …]], …]), liens ([[titre, url, détail], …]),
    scores_basics ({nom: score des audits Opquast basics d'eServices Manager}), jalons ([[classe, libellé], …]), pied (texte).
    """
    f = chemin or RACINE / "referentiel" / "suivi-complements.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}


def construire_services() -> list[dict]:
    """Un onglet par site du parc (écrans tirés du CSV), puis un par compte e-mail ; compléments optionnels par-dessus."""
    import csv
    from urllib.parse import urlsplit
    ecrans = list(csv.DictReader((RACINE / "scripts" / "ecrans_en_ligne.csv").open(encoding="utf-8")))
    sup = COMPLEMENTS.get("services", {})
    out = []
    for site in parc.sites():
        nom = site["nom"]
        ec = [x for x in ecrans if x["service"] == nom]
        accueil = next((x["url"] for x in ec if x["gabarit"].startswith("Accueil")), ec[0]["url"] if ec else "")
        plateforme = site.get("plateforme") or "shopify"
        u = [(x["gabarit"], (urlsplit(x["url"]).path or "/") + (f"?{urlsplit(x['url']).query}" if urlsplit(x["url"]).query else "")) for x in ec]
        s_ = {"id": ident(nom), "nom": nom, "cat": "E-commerce", "reseau": nom,
              "desc": f"Site du parc, plateforme {plateforme}" + (f", version auditée sous {site['prefixe_langue']}" if site.get("prefixe_langue") else "") + ".",
              "version": f"Production · {accueil}", "regles": "Opquast, 245 règles + axe-core (WCAG 2.1 A et AA)", "ecrans": u,
              "tests": [("", "Contrôles réseau", "controles_reseau.py", "RESEAU", "RESEAU")],
              "afaire": ["Corriger en priorité les non-conformités de l'onglet (voir recommandations)"]}
        out.append({**s_, **sup.get(nom, {})})
    for site in parc.sites():
        compte = site.get("compte_email")
        if not compte:
            continue
        s_ = {"id": ident(compte), "nom": compte, "cat": "CRM", "reseau": None,
              "desc": f"Compte e-mail associé à {site['nom']} : e-mails et formulaires d'inscription.",
              "version": "Production · lecture seule", "regles": "Checklist e-mail (referentiel/checklist-email.csv)",
              "ecrans": [(l, c) for c, l in ecrans_email(compte)], "tests": [],
              "afaire": ["Relire les jugements IA et finaliser l'audit", "Tester à la main désinscription, clavier et rendu en mode sombre"]}
        out.append({**s_, **sup.get(compte, {})})
    return out


def ecrans_email(compte: str) -> list[tuple[str, str]]:
    """(code, libellé) des écrans e-mail d'un compte : ceux de l'état consolidé, sinon les 6 écrans types du préfixe du site."""
    pre = next((f"{s['prefixe_pages']}-EM-" for s in parc.sites() if s.get("compte_email") == compte), "")
    lib = dict(SUFFIXES_EMAIL)
    codes = list(dict.fromkeys(c for v in ETAT.get("emails", {}).get(compte, {}).values() for c in v.get("ecrans", {})))
    if not codes:
        return [(pre + k, l) for k, l in SUFFIXES_EMAIL]
    rang = {k: i for i, (k, _) in enumerate(SUFFIXES_EMAIL)}
    suf = lambda c: re.sub(r"^.*?-EM-", "", c)
    return [(c, lib.get(suf(c), suf(c).capitalize())) for c in sorted(codes, key=lambda c: (rang.get(suf(c), len(rang)), c))]


def e(t: str) -> str:
    return html.escape(t, quote=True)


def pastille(statut: str, libelle: str | None = None) -> str:
    cls, txt = PASTILLE.get(statut, ("p-na", statut))
    return f'<span class="pill {cls}">{e(libelle or txt)}</span>'


def bloc_reseau(donnees: dict) -> str:
    pages = donnees["pages"]
    site = sorted(donnees["site"], key=lambda r: r["rule_number"])
    regles_page = sorted({c["rule_number"] for p in pages for c in p["controles"]})
    out = ['<h3>Contrôles réseau, 19 règles Opquast</h3>',
           '<p class="note">Script <code>controles_reseau.py</code> v0.1.2 : contrôles déterministes, même entrée, même résultat. Survolez une pastille pour voir le détail.</p>',
           '<h4>Au niveau du site</h4><div class="tbl"><table class="compact"><thead><tr><th>Règle</th><th>Contrôle</th><th>Statut</th><th>Détail</th></tr></thead><tbody>']
    for r in site:
        out.append(f'<tr><td class="num">{r["rule_number"]}</td><td>{e(REGLES[r["rule_number"]])}</td>'
                   f'<td>{pastille(r["status"])}</td><td>{e(r["comment"])}</td></tr>')
    out.append('</tbody></table></div>')
    out.append('<h4>Page par page</h4><div class="tbl"><table class="matrix"><thead><tr><th>Règle</th>')
    for p in pages:
        out.append(f'<th>{e(p["gabarit"].replace(" (avec formulaire newsletter)", ""))}</th>')
    out.append('</tr></thead><tbody>')
    for n in regles_page:
        out.append(f'<tr><td><span class="num">{n}</span> {e(REGLES[n])}</td>')
        for p in pages:
            c = next((c for c in p["controles"] if c["rule_number"] == n), None)
            if not c:
                out.append('<td>-</td>')
                continue
            cls, txt = PASTILLE.get(c["status"], ("p-na", c["status"]))
            court = {"conforme": "✓", "non-conforme": "✗", "non-testé": "?", "non-applicable": "NA"}.get(c["status"], "·")
            out.append(f'<td><span class="cell {cls}" title="{e(txt + " : " + c["comment"])}" aria-label="{e(txt)}">{court}</span></td>')
        out.append('</tr>')
    out.append('</tbody></table></div>')
    out.append('<p class="legend-line"><span class="cell p-done">✓</span> conforme <span class="cell p-block">✗</span> non conforme '
               '<span class="cell p-na">?</span> non testé (page bloquée pour le robot, code 429)</p>')
    out.append('<h4>Poids du HTML</h4><div class="tbl"><table class="compact"><thead><tr><th>Page</th><th>Code</th><th>Transféré</th>'
               '<th>Décompressé</th><th>Scripts / styles / images</th><th>Tiers sans integrity</th></tr></thead><tbody>')
    for p in pages:
        w = p["poids"]
        if w:
            out.append(f'<tr><td>{e(p["gabarit"])}</td><td class="num">{p["statut_http"]}</td>'
                       f'<td class="num">{w["html_transfere_octets"] / 1024:.0f} Ko</td><td class="num">{w["html_decompresse_octets"] / 1024:.0f} Ko</td>'
                       f'<td class="num">{w["scripts"]} / {w["styles"]} / {w["images"]}</td><td class="num">{w["tiers_sans_integrity"]}</td></tr>')
        else:
            out.append(f'<tr><td>{e(p["gabarit"])}</td><td class="num">{p["statut_http"]}</td><td colspan="4">{pastille("non-testé")}</td></tr>')
    out.append('</tbody></table></div>')
    return "\n".join(out)



CSS_ONGLETS = """
/* Onglets */
.tabs { display: flex; flex-wrap: wrap; gap: 6px; margin: 0; padding: 0; list-style: none; border-bottom: 1px solid var(--line); padding-bottom: 10px; }
.tabs a { display: inline-block; padding: 6px 12px; border-radius: 8px; font-size: 14px; text-decoration: none; color: var(--ink); border: 1px solid var(--line); background: var(--surface); }
.tabs a small { color: var(--muted); font-size: 11.5px; margin-left: 4px; }
.tabs a[aria-selected="true"] { background: var(--accent); color: var(--bg); border-color: var(--accent); }
.tabs a[aria-selected="true"] small { color: var(--bg); opacity: .8; }
.tab { display: grid; gap: 22px; }
.tab[hidden], tr[hidden] { display: none; }
.svc-head { display: grid; gap: 6px; }
.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; margin: 0; }
.facts div { background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 10px 14px; min-width: 0; }
.facts dt { font: 500 11px var(--f-mono); text-transform: uppercase; letter-spacing: .05em; color: var(--muted); }
.facts dd { margin: 2px 0 0; overflow-wrap: anywhere; }
h4 { font: 600 13px/1.3 var(--f-body); margin: 4px 0 8px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
.note, .legend-line { margin: 0; color: var(--muted); font-size: 13.5px; }
details.acc { border: 1px solid var(--line); border-radius: 12px; background: var(--surface); }
details.acc > summary { cursor: pointer; padding: 14px 16px; list-style: none; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 4px 12px; }
details.acc > summary::-webkit-details-marker { display: none; }
details.acc > summary .acc-t { font: 600 16px/1.3 var(--f-body); }
details.acc > summary .acc-t::before { content: "+"; display: inline-block; width: 1.2em; font-family: var(--f-mono); color: var(--accent); }
details.acc[open] > summary .acc-t::before { content: "-"; }
details.acc > summary .acc-r { color: var(--muted); font-size: 13px; }
details.acc > summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 12px; }
.acc-body { padding: 0 16px 16px; display: grid; gap: 12px; min-width: 0; }
details.ex { margin-top: 6px; }
.tbl td:has(details.ex) { min-width: 320px; }
table.baro-table { min-width: 980px; }
.viz-grille { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 400px), 1fr)); gap: 12px; }
.viz svg { max-width: 560px; }
.viz { margin: 0; padding: 12px 14px; border: 1px solid var(--line); border-radius: 12px; background: var(--surface);
  --v-1: #2a78d6; --v-c: #0ca30c; --v-nc: #d03b3b; --v-nt: #fab219; --v-na: #a8a69d; --v-af: #e2e0d8; --v-track: rgba(128,128,128,.12); }
@media (prefers-color-scheme: dark) { :root:where(:not([data-theme="light"])) .viz { --v-1: #3987e5; --v-na: #77766f; --v-af: #3b3b38; --v-track: rgba(255,255,255,.07); } }
:root[data-theme="dark"] .viz { --v-1: #3987e5; --v-na: #77766f; --v-af: #3b3b38; --v-track: rgba(255,255,255,.07); }
.viz figcaption { font: 600 13.5px/1.3 var(--f-body); margin-bottom: 6px; }
.viz svg { width: 100%; height: auto; display: block; overflow: visible; }
.viz .v-lab { font: 12px var(--f-body); fill: var(--muted); }
.viz .v-val { font: 600 12px var(--f-mono); fill: var(--ink); }
.viz .v-bar { fill: var(--v-1); } .viz .v-track { fill: var(--v-track); }
.viz .v-c { fill: var(--v-c); } .viz .v-nc { fill: var(--v-nc); } .viz .v-nt { fill: var(--v-nt); } .viz .v-na { fill: var(--v-na); } .viz .v-af { fill: var(--v-af); }
.viz g:hover rect:not(.v-track) { opacity: .8; }
.v-leg { list-style: none; display: flex; flex-wrap: wrap; gap: 4px 12px; margin: 0 0 6px; padding: 0; font-size: 12px; color: var(--muted); }
.v-leg i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }
.v-leg i.v-c { background: var(--v-c); } .v-leg i.v-nc { background: var(--v-nc); } .v-leg i.v-nt { background: var(--v-nt); } .v-leg i.v-na { background: var(--v-na); } .v-leg i.v-af { background: var(--v-af); }
ul.mini { margin: 0; padding-left: 16px; display: grid; gap: 4px; }
table.baro-table td { vertical-align: top; font-size: 13.5px; }
table.baro-table td:first-child { min-width: 230px; }
table.baro-table td.c-afaire { color: var(--muted); }
table.baro-table tr.synthese td { background: var(--bg); }
details.ex > summary { cursor: pointer; font-size: 12.5px; color: var(--accent); }
details.ex pre { white-space: pre-wrap; overflow-wrap: anywhere; font: 12px/1.45 var(--f-mono); background: var(--bg); border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; margin: 6px 0 4px; }
.copier { font: 12px var(--f-body); padding: 2px 10px; border-radius: 6px; border: 1px solid var(--line); background: var(--surface); color: var(--ink); cursor: pointer; }
.trois { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; }
.carte { border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; background: var(--bg); display: grid; gap: 6px; align-content: start; }
.carte h4 { text-transform: none; letter-spacing: 0; color: var(--ink); font-size: 14px; margin: 0; }
.carte p { margin: 0; font-size: 13.5px; }
.legend-line { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; }
table.compact { min-width: 640px; }
table.matrix { min-width: 760px; }
table.matrix td, table.matrix th { text-align: center; padding: 7px 8px; }
table.matrix td:first-child, table.matrix th:first-child { text-align: left; }
table.matrix td:nth-child(2), table.matrix th:nth-child(2) { text-align: left; min-width: 280px; }
.cell { display: inline-grid; place-items: center; width: 24px; height: 22px; border-radius: 6px; font: 600 12px/1 var(--f-mono); }
td.tool { font: 12.5px var(--f-mono); color: var(--muted); }
.two { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; align-items: start; }
.two > div { min-width: 0; }
ul.screens { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
ul.screens li { display: grid; gap: 2px; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px; min-width: 0; }
ul.screens code { overflow-wrap: anywhere; background: none; padding: 0; color: var(--muted); }
.explain { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 16px 20px; display: grid; gap: 8px; max-width: 80ch; }
.explain p { margin: 0; }
.filters { display: flex; flex-wrap: wrap; gap: 8px 12px; align-items: center; }
.filters label { font: 500 12px var(--f-mono); color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
.filters input, .filters select { font: 14px var(--f-body); padding: 6px 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface); color: var(--ink); min-width: 0; }
.filters input { flex: 1 1 220px; }
.filters .count { color: var(--muted); font-size: 13px; }
.hint { color: var(--muted); font-size: 12px; }
ul.plain { margin: 0; padding-left: 18px; display: grid; gap: 6px; max-width: 90ch; }
table.refs td { min-width: 150px; }
table.refs small { color: var(--muted); }
.tabs-nav { display: grid; gap: 10px; border-bottom: 1px solid var(--line); padding-bottom: 12px; }
.tabs-nav .tabs { border-bottom: 0; padding-bottom: 0; }
.tabs-main a { font-weight: 600; }
.tabs-sub { display: flex; flex-wrap: wrap; gap: 6px 10px; align-items: center; }
.sub-label { font: 500 11px var(--f-mono); text-transform: uppercase; letter-spacing: .05em; color: var(--muted); min-width: 64px; }
.tabs-main a.t-sites { border-left: 4px solid var(--accent); }
.tabs-main a.t-mails { border-left: 4px solid var(--todo); }
.baros { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.baro { display: grid; gap: 4px; padding: 20px 22px; border-radius: 14px; border: 1px solid var(--line); background: var(--surface); color: var(--ink); text-decoration: none; }
.baro b { font: 700 26px/1.1 var(--f-display); }
.baro span { color: var(--muted); font-size: 14px; }
.baro .go { color: var(--accent); font-weight: 600; margin-top: 6px; }
.baro-sites { border-top: 5px solid var(--accent); }
.baro-mails { border-top: 5px solid var(--todo); }
.baro:hover, .baro:focus-visible { border-color: var(--accent); }
"""

JS_ONGLETS = """
<script>document.addEventListener('click',function(ev){var a=ev.target.closest('a.ancre');if(!a)return;var el=document.getElementById(a.getAttribute('href').slice(1));if(!el)return;ev.preventDefault();if(el.dataset.ouvre)el=document.getElementById(el.dataset.ouvre);var d=el.closest('details')||el;while(d){if(d.tagName==='DETAILS')d.open=true;d=d.parentElement&&d.parentElement.closest('details');}el.scrollIntoView({block:'start'});});</script>
<script>document.addEventListener('click',function(ev){var b=ev.target.closest('.copier');if(!b)return;var t=b.parentNode.querySelector('pre').innerText;try{navigator.clipboard.writeText(t).then(function(){b.textContent='Copié';setTimeout(function(){b.textContent='Copier'},1500)})}catch(e){}});</script>
<script>
(function () {
  var liens = document.querySelectorAll('.tabs a');
  var panneaux = document.querySelectorAll('.tab');
  function montrer() {
    var id = (location.hash || '#ensemble').slice(1);
    if (!document.getElementById(id)) id = 'ensemble';
    panneaux.forEach(function (p) { p.hidden = p.id !== id; });
    liens.forEach(function (a) { a.setAttribute('aria-selected', a.getAttribute('href') === '#' + id ? 'true' : 'false'); });
  }
  function caler() { var n = document.querySelector('.tabs-nav'); if (n && location.hash) n.scrollIntoView({ block: 'start' }); }
  window.addEventListener('hashchange', function () { montrer(); caler(); });
  var ft = document.getElementById('f-texte'), fs = document.getElementById('f-theme'), fc = document.getElementById('f-compte');
  function filtrer() {
    var q = (ft.value || '').toLowerCase(), th = fs.value, n = 0;
    document.querySelectorAll('#t-regles tbody tr').forEach(function (tr) {
      var ok = (!th || tr.getAttribute('data-theme').indexOf(th) !== -1) && (!q || tr.textContent.toLowerCase().indexOf(q) !== -1);
      tr.hidden = !ok; if (ok) n++;
    });
    fc.textContent = n + (n > 1 ? ' règles' : ' règle');
  }
  if (ft && fs) { ft.addEventListener('input', filtrer); fs.addEventListener('change', filtrer); }
  var et = document.getElementById('e-texte'), es = document.getElementById('e-statut'), eh = document.getElementById('e-theme'), ec = document.getElementById('e-compte');
  function filtrerEtat() {
    var q = (et.value || '').toLowerCase(), st = es.value, th = eh.value, n = 0;
    document.querySelectorAll('#t-etat tbody tr').forEach(function (tr) {
      var ok = (!st || (' ' + tr.getAttribute('data-statut') + ' ').indexOf(' ' + st + ' ') !== -1) && (!th || tr.getAttribute('data-theme').indexOf(th) !== -1) && (!q || tr.textContent.toLowerCase().indexOf(q) !== -1);
      tr.hidden = !ok; if (ok) n++;
    });
    ec.textContent = n + (n > 1 ? ' règles' : ' règle');
  }
  document.querySelectorAll('select.f-etat').forEach(function (sel) {
    function f() {
      var t = document.getElementById(sel.getAttribute('data-table')), v = sel.value, n = 0;
      t.querySelectorAll('tbody tr').forEach(function (tr) { var ok = !v || tr.getAttribute('data-statut') === v; tr.hidden = !ok; if (ok) n++; });
      var c = document.getElementById(sel.getAttribute('data-table') + '-compte'); if (c) c.textContent = n + (n > 1 ? ' lignes' : ' ligne');
    }
    sel.addEventListener('change', f); f();
  });
  if (et && es && eh) { et.addEventListener('input', filtrerEtat); es.addEventListener('change', filtrerEtat); eh.addEventListener('change', filtrerEtat); filtrerEtat(); }
  montrer();
  caler();
})();
</script>
"""


# Listes « Fait » et « À faire » de la vue d'ensemble et liens : propres à une mission, lus dans les compléments
# optionnels (referentiel/suivi-complements.json) par main() ; vides sinon.
FAIT: list = []
A_FAIRE: list = []
LIENS: list = []


def liens_locaux(chemin: Path = RACINE / "liens-locaux.json") -> list[tuple[str, str, str]]:
    """Liens propres à un compte (Artifacts publiés, par exemple), gardés hors dépôt.

    Format : [{"titre": "...", "url": "...", "detail": "..."}, ...]
    """
    if not chemin.is_file():
        return []
    return [(lien["titre"], lien["url"], lien.get("detail", "")) for lien in json.loads(chemin.read_text(encoding="utf-8"))]




def onglet_referentiels() -> str:
    import csv
    regles = json.loads((RACINE / "referentiel" / "opquast-checklist-v5.json").read_text(encoding="utf-8"))
    themes = sorted({t for r in regles for t in r["metadata"].get("Thématiques", [])})
    email = list(csv.DictReader((RACINE / "referentiel" / "checklist-email.csv").open(encoding="utf-8")))
    o = ['<section class="tab" id="referentiels" role="tabpanel" aria-labelledby="t-referentiels" hidden>',
         '<div class="svc-head"><div class="eyebrow">Référentiels</div><h2>Les règles appliquées</h2>',
         '<p class="lede">Le baromètre des sites applique les 245 règles d\'Opquast et les règles WCAG d\'axe-core ; le baromètre des e-mails applique la checklist e-mail du kit.</p></div>',
         '<div class="explain"><h3>C\'est quoi, les 245 règles ?</h3>',
         '<p>Le référentiel <strong>Opquast « Qualité numérique », version 5 (2025-2030)</strong> rassemble 245 bonnes pratiques que tout site web devrait respecter, '
         'quel que soit son secteur. Il est collaboratif, publié en licence ouverte, en français, anglais et espagnol. Chaque règle est formulée pour être '
         'vérifiable : elle est respectée ou non, sans débat d\'expert.</p>',
         '<p>Les règles sont rangées en <strong>14 thèmes</strong> (contenus, données personnelles, e-commerce, formulaires, sécurité…) et portent des '
         '<strong>étiquettes</strong> : 128 touchent l\'accessibilité, 40 le référencement, 32 l\'écoconception, 21 la vie privée, 65 forment le socle « Basics ».</p>',
         '<p class="note">Les sites du parc reçoivent les 245 règles. Le MCP Opquast en classe 34 automatisables (réseau), 102 semi-automatiques (code de la page) et 109 manuelles (visuel).</p></div>',
         '<div class="explain"><h3>Et axe-core ?</h3><p><strong>axe-core</strong> (Deque, open source) vérifie automatiquement les règles WCAG 2.1 A et AA, la base de la norme EN 301 549 qu\'exige l\'European Accessibility Act pour les sites e-commerce depuis juin 2025. Il complète Opquast sur l\'accessibilité sans le coût d\'un audit RGAA complet. Il tourne dans le navigateur (<code>scripts/axe_navigateur.js</code>) ou par le robot d\'eServices Manager.</p></div>',
         '<h3>Opquast, 245 règles</h3>',
         '<div class="filters"><label for="f-texte">Rechercher</label><input id="f-texte" type="search" placeholder="numéro, mot, étiquette…">',
         '<label for="f-theme">Thème</label><select id="f-theme"><option value="">Tous les thèmes</option>']
    o += [f'<option value="{e(t)}">{e(t)}</option>' for t in themes]
    o.append('</select><span class="count" id="f-compte" aria-live="polite">245 règles</span></div>')
    meth = {int(x["numero"]): x["methode"] for x in csv.DictReader((RACINE / "referentiel" / "repartition-regles.csv").open(encoding="utf-8"))}
    LIB = {"IA": ("ko", "IA"), "réseau": ("ok", "script réseau"), "page": ("ok", "code de la page"), "écartée": ("info", "écartée pour l'instant")}
    o.append('<div class="tbl"><table class="compact" id="t-regles"><thead><tr><th>N°</th><th>Thème</th><th>Règle</th><th>Méthode</th><th>Étiquettes</th></tr></thead><tbody>')
    for r in regles:
        th = ", ".join(r["metadata"].get("Thématiques", []))
        tags = ", ".join(r["metadata"].get("Tags", []))
        m = LIB.get(meth.get(r["number"], ""), ("info", "?"))
        o.append(f'<tr data-theme="{e(th)}"><td class="num">{r["number"]}</td><td>{e(th)}</td><td>{e(r["description"]["fr"])}</td><td>{pastille(m[0], m[1])}</td><td class="tool">{e(tags)}</td></tr>')
    o.append('</tbody></table></div>')
    o.append(f'<h3>Checklist e-mail, {len(email)} critères</h3>'
             '<p class="note">Pour les comptes e-mail : critères propres aux e-mails et aux formulaires, tirés du W3C (WCAG), de l\'aide des outils d\'envoi, de la CNIL, '
             'du CPCE, des exigences de Gmail et Yahoo et, pour le mode sombre, des tableaux open source Can I Email. Détail et sources : <code>referentiel/checklist-email.md</code>.</p>')
    o.append('<div class="tbl"><table class="compact"><thead><tr><th>Id</th><th>Thème</th><th>Critère</th><th>Vérification</th><th>Opquast</th><th>Source</th></tr></thead><tbody>')
    for c in email:
        o.append(f'<tr><td class="num">{e(c["id"])}</td><td>{e(c["theme"])}</td><td>{e(c["critere"])}</td><td>{e(c["verification"])}</td>'
                 f'<td class="num">{e(c["regle_opquast"]) or "-"}</td><td class="tool">{e(c["source"])}</td></tr>')
    o.append('</tbody></table></div></section>')
    return "\n".join(o)


CODE_PASTILLE = {"C": "conforme", "NC": "non-conforme", "NA": "non-applicable", "NT": "non-testé", "I": "indéterminé"}


RECO_GEN = {x["code"]: x["recommandation"] for x in __import__("csv").DictReader((RACINE / "referentiel" / "recommandations.csv").open(encoding="utf-8"))} if (RACINE / "referentiel" / "recommandations.csv").exists() else {}


def onglet_etat() -> str:
    fichiers = sorted(RACINE.glob("resultats/etat-*/etat.json"))
    if not fichiers:
        return ""
    d = json.loads(fichiers[-1].read_text(encoding="utf-8"))
    sites = d["sites"]
    noms = list(sites)
    o = ['<section class="tab" id="etat" role="tabpanel" aria-labelledby="t-etat" hidden>',
         '<div class="svc-head"><div class="eyebrow">Résultats du ' + e(d["date"]) + '</div><h2>État de chaque règle et recommandations</h2>',
         '<p class="lede">Toutes les mesures réunies, règle par règle et site par site : nos scripts sans IA (contrôles réseau, code de la page, '
         'W3C i18n Checker, REDbot) et le robot d\'eServices Manager (Opquast basics). Une règle est non conforme sur un site dès qu\'une page '
         'l\'est, quelle que soit la source. Chaque non-conformité a sa recommandation ; le détail adapté à chaque site (pages, constat, audit eServices Manager) est dans l\'onglet du site.</p></div>',
         '<div class="explain"><h3>Comment lire</h3><p>Un site, une colonne. Survolez une pastille pour voir la source et la preuve. '
         '« Non testé » : la règle n\'a été mesurée par aucun outil sur ce site (pages refusées par Shopify, règle hors périmètre de l\'outil). '
         'Les règles écartées pour l\'instant n\'apparaissent pas. Tout est aussi saisi dans eServices Manager : un audit « scripts sans IA » '
         'et un audit Opquast basics par site.</p></div>',
         '<h3>Bilan par site</h3><div class="tbl"><table class="compact"><thead><tr><th>Site</th><th>Règles mesurées</th><th>Conformes</th>'
         '<th>Non conformes</th><th>Non applicables</th><th>Non testées</th><th>Taux de conformité</th></tr></thead><tbody>']
    for nom in noms:
        st = [v["statut"] for v in sites[nom].values()]
        c, nc, na, nt = (st.count(x) for x in ("C", "NC", "NA", "NT"))
        taux = f"{100 * c / (c + nc):.0f} %" if c + nc else "-"
        o.append(f'<tr><td>{e(nom)}</td><td class="num">{len(st)}</td><td class="num">{c}</td><td class="num">{nc}</td>'
                 f'<td class="num">{na}</td><td class="num">{nt}</td><td class="num"><strong>{taux}</strong></td></tr>')
    o.append('</tbody></table></div><p class="note">Taux = conformes / (conformes + non conformes). À comparer avec prudence : '
             'le nombre de règles mesurées varie d\'un site à l\'autre selon les pages que Shopify a laissées passer.</p>')
    regles = sorted({n for v in sites.values() for n in v}, key=int)
    themes = sorted({sites[nom][n]["theme"] for nom in noms for n in sites[nom]})
    o.append('<h3>Règles Opquast, site par site</h3>'
             '<div class="filters"><label for="e-texte">Rechercher</label><input id="e-texte" type="search" placeholder="numéro, mot…">'
             '<label for="e-statut">Statut</label><select id="e-statut"><option value="">Tous</option><option value="NC" selected>Non conforme sur au moins un site</option>'
             '<option value="C">Conforme partout</option><option value="NT">Non testé quelque part</option></select>'
             '<label for="e-theme">Thème</label><select id="e-theme"><option value="">Tous les thèmes</option>')
    o += [f'<option value="{e(t)}">{e(t)}</option>' for t in themes]
    o.append(f'</select><span class="count" id="e-compte" aria-live="polite">{len(regles)} règles</span></div>')
    o.append('<div class="tbl"><table class="compact" id="t-etat"><thead><tr><th>N°</th><th>Règle</th>'
             + "".join(f'<th>{e(n)}</th>' for n in noms) + '<th>Recommandation</th></tr></thead><tbody>')
    for n in regles:
        lignes = [sites[nom].get(n) for nom in noms]
        ref = next(x for x in lignes if x)
        sts = [x["statut"] if x else "NT" for x in lignes]
        filtre = ("NC " if "NC" in sts else "") + ("C " if all(x == "C" or x == "NA" for x in sts) else "") + ("NT" if "NT" in sts else "")
        cells = []
        for x in lignes:
            if not x:
                cells.append(f'<td>{pastille("non-testé")}</td>')
                continue
            src = "scripts : " + (x["scripts"] or "-") + " ; robot basics : " + (x["robot"] or "-")
            preuve = " ; " + " | ".join(x["determinant"]) if x["determinant"] else ""
            cells.append(f'<td title="{e(src + preuve)}">{pastille(CODE_PASTILLE[x["statut"]])}</td>')
        reco = RECO_GEN.get(n, "") if "NC" in sts else ""
        o.append(f'<tr data-statut="{filtre.strip()}" data-theme="{e(ref["theme"])}"><td class="num">{n}</td><td>{e(ref["titre"])}'
                 f'<br><small>{e(ref["theme"])} · {e(ref["methode"] or "")}</small></td>' + "".join(cells) + f'<td>{e(reco)}</td></tr>')
    o.append('</tbody></table></div>')
    for compte, crits in d.get("emails", {}).items():
        st = [v["statut"] for v in crits.values()]
        ECRANS_EMAIL = ecrans_email(compte)
        o.append(f'<h3>E-mails : {e(compte)}</h3><p class="note">{len(st)} critères de la checklist e-mail sur {len(ECRANS_EMAIL)} écrans ({e(", ".join(l.lower() for _, l in ECRANS_EMAIL))}) : '
                 f'{st.count("NC")} critères non conformes sur au moins un écran, {st.count("C")} conformes partout. '
                 'Évaluation par script et par IA (Claude), compte en lecture seule ; importée dans eServices Manager.</p>')
        o.append('<div class="tbl"><table class="compact"><thead><tr><th>Critère</th><th>Intitulé</th>'
                 + "".join(f'<th>{e(l)}</th>' for _, l in ECRANS_EMAIL) + '<th>Recommandation</th></tr></thead><tbody>')
        for k, v in sorted(crits.items()):
            cells = "".join(f'<td title="{e(v["ecrans"].get(c, ["", ""])[1])}">{pastille(CODE_PASTILLE.get(v["ecrans"].get(c, ["NT"])[0], "non-testé"))}</td>' for c, _ in ECRANS_EMAIL)
            o.append(f'<tr><td class="num">{e(k)}</td><td>{e(v["titre"])}<br><small>{e(v["theme"])}</small></td>{cells}<td>{e(RECO_GEN.get(k, "") if v["statut"] == "NC" else "")}</td></tr>')
        o.append('</tbody></table></div>')
    o.append('</section>')
    return "\n".join(o)



def charger_etat() -> dict:
    f = sorted(RACINE.glob("resultats/etat-*/etat.json"))
    return json.loads(f[-1].read_text(encoding="utf-8")) if f else {}


ETAT: dict = {}


def liens_audits(sources: list) -> str:
    return "<br>".join(f'<a href="{e(x["url"])}" target="_blank" rel="noopener">{e(x["nom"])}</a> <small>({e({"C": "conforme", "NC": "non conforme", "NA": "non applicable", "NT": "non testé"}.get(x["statut"], x["statut"]))})</small>' for x in sources)


def bloc_etat_site(s: dict) -> str:
    regles = ETAT.get("sites", {}).get(s["nom"])
    if not regles:
        return ""
    sid = s["id"]
    st = [v["statut"] for v in regles.values()]
    c, nc, na, nt = (st.count(x) for x in ("C", "NC", "NA", "NT"))
    taux = f"{100 * c / (c + nc):.0f} %" if c + nc else "-"
    audits = {}
    for v in regles.values():
        for x in v["sources"]:
            audits[x["url"]] = x["nom"]
    o = ['<h3>Toutes les règles mesurées et recommandations</h3>',
         f'<p class="note">{len(st)} règles Opquast mesurées sur ce site : <strong>{c} conformes, {nc} non conformes</strong>, {na} non applicables, {nt} non tranchées. '
         f'Taux de conformité : <strong>{taux}</strong>. Une règle est non conforme dès qu\'une page l\'est, quelle que soit la source. '
         'La colonne « Résultat » donne ce qui tranche (outil, page, constat) ; la colonne « Audit » renvoie vers l\'audit eServices Manager où le résultat est saisi.</p>',
         '<ul class="plain">' + "".join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(n)}</a></li>' for u, n in audits.items()) + '</ul>',
         f'<div class="filters"><label for="fs-{sid}">Statut</label><select id="fs-{sid}" class="f-etat" data-table="te-{sid}">'
         '<option value="">Tous</option><option value="NC" selected>Non conformes</option><option value="C">Conformes</option>'
         '<option value="NA">Non applicables</option><option value="NT">Non tranchées</option></select>'
         f'<span class="count" id="te-{sid}-compte" aria-live="polite"></span></div>',
         f'<div class="tbl"><table class="compact" id="te-{sid}"><thead><tr><th>N°</th><th>Règle</th><th>Statut</th><th>Résultat qui tranche</th><th>Audit</th><th>Recommandation</th></tr></thead><tbody>']
    ordre = {"NC": 0, "NT": 1, "C": 2, "NA": 3}
    for n, v in sorted(regles.items(), key=lambda kv: (ordre[kv[1]["statut"]], int(kv[0]))):
        det = "<br>".join(e(x) for x in v["determinant"])
        if v["pages_nc"]:
            det += f'<br><small>Pages non conformes : {e(", ".join(v["pages_nc"]))}</small>'
        o.append(f'<tr data-statut="{v["statut"]}"><td class="num">{n}</td><td>{e(v["titre"])}<br><small>{e(v["theme"])} · {e(v["methode"] or "")}</small></td>'
                 f'<td>{pastille(CODE_PASTILLE[v["statut"]])}</td><td>{det}</td><td>{liens_audits(v["sources"])}</td><td>{e(v["recommandation"])}</td></tr>')
    o.append('</tbody></table></div>')
    return "\n".join(o)


def bloc_etat_email(s: dict) -> str:
    compte = s["nom"]
    crits = ETAT.get("emails", {}).get(compte)
    if not crits:
        return ""
    sid = s["id"]
    ECRANS_EMAIL = ecrans_email(compte)
    st = [v["statut"] for v in crits.values()]
    src = next(iter(crits.values()))["source"]
    o = [f'<h3>Les {len(st)} critères, écran par écran, et recommandations</h3>',
         f'<p class="note">{st.count("NC")} critères non conformes sur au moins un écran, {st.count("C")} conformes, {st.count("NA")} non applicables, '
         f'{st.count("NT") + st.count("I")} non tranchés (parcours réels, captures en mode sombre). Évaluation par script et par IA (Claude), compte en lecture seule. '
         f'Audit : <a href="{e(src["url"])}" target="_blank" rel="noopener">{e(src["nom"])}</a>. Survolez une pastille pour voir le résultat de l\'écran.</p>',
         f'<div class="filters"><label for="fs-{sid}">Statut</label><select id="fs-{sid}" class="f-etat" data-table="te-{sid}">'
         '<option value="">Tous</option><option value="NC" selected>Non conformes</option><option value="C">Conformes</option>'
         '<option value="NA">Non applicables</option><option value="NT">Non tranchés</option></select>'
         f'<span class="count" id="te-{sid}-compte" aria-live="polite"></span></div>',
         f'<div class="tbl"><table class="compact" id="te-{sid}"><thead><tr><th>Critère</th><th>Intitulé</th>'
         + "".join(f'<th>{e(l)}</th>' for _, l in ECRANS_EMAIL) + '<th>Résultat qui tranche</th><th>Recommandation</th></tr></thead><tbody>']
    for k, v in sorted(crits.items()):
        stf = "NT" if v["statut"] == "I" else v["statut"]
        cells = "".join(f'<td title="{e(v["ecrans"].get(c, ["", ""])[1])}">{pastille(CODE_PASTILLE.get(v["ecrans"].get(c, ["NT"])[0], "non-testé"))}</td>' for c, _ in ECRANS_EMAIL)
        cle = next((c for c, val in v["ecrans"].items() if val[0] == v["statut"]), None)
        det = (dict(ECRANS_EMAIL).get(cle, "") + " : " + v["ecrans"][cle][1]) if cle else ""
        o.append(f'<tr data-statut="{stf}"><td class="num">{e(k)}</td><td>{e(v["titre"])}<br><small>{e(v["theme"])}</small></td>{cells}<td>{e(det)}</td><td>{e(v["recommandation"])}</td></tr>')
    o.append('</tbody></table></div>')
    return "\n".join(o)


def TAUX_NAV(nom: str) -> str:
    v = ETAT.get("sites", {}).get(nom) or ETAT.get("emails", {}).get(nom)
    if not v:
        return "à faire"
    st = [x["statut"] for x in v.values()]
    c, nc = st.count("C"), st.count("NC")
    return f"{100 * c / (c + nc):.0f} %" if c + nc else "à faire"


def RESUME_SITES() -> str:
    sites = ETAT.get("sites", {})
    if not sites:
        return "contrôles en cours"
    t = []
    for v in sites.values():
        st = [x["statut"] for x in v.values()]
        c, nc = st.count("C"), st.count("NC")
        t.append(100 * c / (c + nc) if c + nc else 0)
    return f"{len(sites)} sites mesurés : {min(t):.0f} à {max(t):.0f} % de conformité"


def RESUME_MAILS() -> str:
    m = ETAT.get("emails", {})
    if not m:
        return "0 critère évalué pour l'instant"
    nc = [sum(1 for x in v.values() if x["statut"] == "NC") for v in m.values()]
    attendus = len([1 for s in parc.sites() if s.get("compte_email")])
    reste = f" ; {attendus - len(m)} à connecter" if attendus > len(m) else ""
    return f"{len(m)} compte(s) évalué(s) : {min(nc)} à {max(nc)} critères non conformes{reste}"


def TAUX_SITE(nom: str) -> str:
    v = ETAT.get("sites", {}).get(nom)
    if not v:
        return pastille("afaire", "à faire")
    st = [x["statut"] for x in v.values()]
    c, nc = st.count("C"), st.count("NC")
    return pastille("attention", f"{100 * c / (c + nc):.0f} % conformes, {nc} règles non conformes")


def CRIT_COMPTE(nom: str, total: int) -> str:
    v = ETAT.get("emails", {}).get(nom)
    if not v:
        return pastille("afaire", f"0 sur {total}")
    st = [x["statut"] for x in v.values()]
    return pastille("attention", f"{total - st.count('NT') - st.count('I')} sur {total} tranchés, {st.count('NC')} non conformes")


def SOMBRE_COMPTE(nom: str) -> str:
    v = ETAT.get("emails", {}).get(nom)
    if not v:
        return pastille("afaire", "à vérifier")
    return pastille("ko", "non prévu") if any(v.get(k, {}).get("statut") == "NC" for k in ("EM35", "EM36", "EM37")) else pastille("ok", "prévu")


def THEME_COMPTE(nom: str, theme: str) -> str:
    v = ETAT.get("emails", {}).get(nom)
    if not v:
        return pastille("afaire", "à évaluer")
    st = [x["statut"] for x in v.values() if x["theme"] == theme]
    nc = st.count("NC")
    return pastille("ko" if nc else "ok", f"{nc} non conforme(s) sur {len(st)}" if nc else f"{st.count('C')} conformes, aucun non conforme")


AXE_FR = {  # intitulé français et recommandation des règles axe-core rencontrées
    "button-name": ("Les boutons ont un nom accessible", "Donner un nom à chaque bouton sans texte (aria-label sur les boutons icône : panier, fermer, quantité)."),
    "nested-interactive": ("Pas d'éléments interactifs imbriqués", "Ne pas placer de lien ou bouton dans un autre (cartes produit cliquables contenant un bouton) : séparer les zones cliquables."),
    "link-name": ("Les liens ont un intitulé", "Donner un intitulé aux liens image ou icône (aria-label ou alt de l'image)."),
    "color-contrast": ("Contraste du texte d'au moins 4,5:1", "Foncer les textes et boutons concernés pour atteindre 4,5:1 (3:1 pour les grands textes)."),
    "listitem": ("Les éléments de liste sont dans une liste", "Placer chaque <li> dans un <ul> ou <ol> (menus, carrousels)."),
    "list": ("Les listes ne contiennent que des éléments de liste", "Ne mettre que des <li> directement dans les <ul>/<ol> (pas de div intermédiaire)."),
    "scrollable-region-focusable": ("Les zones défilantes sont accessibles au clavier", "Rendre les zones défilantes focalisables (tabindex=0) ou atteignables par leurs contrôles."),
    "aria-prohibited-attr": ("Attributs ARIA autorisés", "Retirer les attributs ARIA interdits sur ces éléments (aria-label sur un div sans rôle)."),
    "aria-hidden-focus": ("Pas d'élément masqué mais focalisable", "Ne pas mettre aria-hidden sur un contenu qui contient des liens ou boutons atteignables au clavier (tiroirs, carrousels)."),
    "image-alt": ("Les images ont une alternative", "Ajouter un attribut alt à chaque image (vide si décorative)."),
    "meta-viewport": ("Le zoom n'est pas bloqué", "Retirer maximum-scale=1 et user-scalable=no de la meta viewport du thème."),
    "label": ("Les champs ont une étiquette", "Associer une étiquette à chaque champ (label for ou aria-label)."),
    "select-name": ("Les listes déroulantes ont un nom", "Donner un nom accessible aux <select> (label ou aria-label)."),
    "aria-valid-attr-value": ("Valeurs ARIA valides", "Corriger les valeurs ARIA invalides (aria-controls ou aria-labelledby pointant vers un id inexistant)."),
}


def dernier_json(motif: str) -> dict:
    l = sorted(RACINE.glob(motif))
    return json.loads(l[-1].read_text(encoding="utf-8")) if l else {}


EXEMPLES: dict = {}
LECTURE: dict = {}
FICHE: dict = {}
OUTILS_PAGES: dict = {}
OUTILS_LIGNE: dict = {}
PARCOURS_RES: dict = {}
RELEVE: dict = {}


def charger_annexes() -> None:
    maj_abr()
    EXEMPLES.update(json.loads((RACINE / "referentiel" / "exemples.json").read_text(encoding="utf-8")))
    LECTURE.update(dernier_json("resultats/lecture-critique-*/lecture.json"))
    FICHE.update(dernier_json("resultats/contre-examen-*/fiche.json"))
    OUTILS_PAGES.update(dernier_json("resultats/outils-*/pages.json"))
    OUTILS_LIGNE.update(dernier_json("resultats/outils-*/en_ligne.json"))
    PARCOURS_RES.update(dernier_json("resultats/parcours-*/parcours.json"))
    RELEVE.update(dernier_json("resultats/releve-*/decisions.json"))
    AUD.update(json.loads((RACINE / "referentiel" / "audits-esm.json").read_text(encoding="utf-8")))
    import csv
    recos = {x["code"]: x["recommandation"] for x in csv.DictReader((RACINE / "referentiel" / "recommandations.csv").open(encoding="utf-8"))}
    RECOS.update(recos)
    for x in csv.DictReader((RACINE / "referentiel" / "repartition-regles.csv").open(encoding="utf-8")):
        METH[int(x["numero"])] = x["methode"]; RAISON[int(x["numero"])] = x["raison"]
    EXCLUSIONS.update(json.loads((RACINE / "referentiel" / "exclusions-sites.json").read_text(encoding="utf-8")))
    # règles retirées : on ne garde pas le verdict du robot, elles ne sont pas testées
    for nom, regles in ETAT.get("sites", {}).items():
        for n in [k for k in regles if METH.get(int(k)) == "écartée" and k != "33" or int(k) in EXCLUSIONS.get(nom, [])]:
            if METH.get(int(n)) == "écartée" and "Retirée le 12/11" not in RAISON.get(int(n), ""):
                continue
            del regles[n]
    ref = {str(r["number"]): r for r in json.loads((RACINE / "referentiel" / "opquast-checklist-v5.json").read_text(encoding="utf-8"))}
    for nom, lignes in FICHE.items():
        regles = ETAT.get("sites", {}).get(nom, {})
        for x in lignes:
            r = regles.get(str(x["regle"]))
            d = x.get("decision_statut")
            if not r:
                continue
            ce = {"nom": AUD["noms"]["contre_examen"].format(site=nom), "url": AUD["base"] + AUD["contre_examen"][nom], "statut": d or "NT"} if nom in AUD.get("contre_examen", {}) else None
            if ce:
                r["sources"].append(ce)
            if d:
                r["statut"] = d
                r["determinant"].insert(0, f"Contre-examen (tranché par Claude, validé par {qui()}) : " + x["decision_motif"])
                r["recommandation"] = (f"Sur {nom} : " + recos[str(x["regle"])]) if d == "NC" and str(x["regle"]) in recos else ""
            else:
                r["determinant"].insert(0, "Contre-examen : " + x["decision_motif"])
    # règles jusqu'ici écartées, tranchées par le relevé navigateur (mesure ou lecture des pages légales)
    for nom, dec in RELEVE.items():
        regles = ETAT.get("sites", {}).get(nom)
        if regles is None:
            continue
        for k, (st, preuve, nature) in dec.items():
            if k in regles or int(k) in EXCLUSIONS.get(nom, []) or "Retirée le 12/11" in RAISON.get(int(k), ""):
                continue
            regles[k] = {"titre": ref[k]["description"]["fr"], "theme": ", ".join(ref[k]["metadata"].get("Thématiques", [])), "methode": "relevé",
                         "statut": st, "scripts": None, "robot": None, "pages_nc": [],
                         "determinant": [f"Relevé navigateur, {'mesure' if nature == 'mesure' else 'lecture des pages légales et d’aide'} (tranché par Claude, à valider) : {preuve}"],
                         "sources": [], "recommandation": (f"Sur {nom} : " + RECOS[k]) if st == "NC" and k in RECOS else ""}
    # la lecture critique tranche les écarts entre audits : le baromètre reprend le statut retenu
    for nom, l in LECTURE.items():
        if nom.startswith("_"):
            continue
        regles = ETAT.get("sites", {}).get(nom, {})
        for x in l["ecarts"]:
            r = regles.get(x["regle"])
            if r and x["statut"] in ("C", "NC", "NA") and r["statut"] != x["statut"]:
                r["determinant"].insert(0, f"Lecture critique ({x['type']}) : statut retenu {x['statut_lib']}. {x['pourquoi']}")
                r["statut"] = x["statut"]
                if x["statut"] == "NC" and not r.get("recommandation") and x["regle"] in RECOS:
                    r["recommandation"] = f"Sur {nom} : " + RECOS[x["regle"]]
                elif x["statut"] != "NC":
                    r["recommandation"] = ""
    # règles encore « non testé » que les deuxièmes sources (12/11) tranchent de façon concordante
    for nom, l in LECTURE.items():
        if nom.startswith("_"):
            continue
        regles = ETAT.get("sites", {}).get(nom, {})
        for k, st in (l.get("statut_sources") or {}).items():
            r = regles.get(k)
            if r and r["statut"] == "NT" and st in ("C", "NC", "NA"):
                src = [a for a in l["sources_par_regle"].get(k, [])]
                r["determinant"].insert(0, f"Tranchée par les sources concordantes ({', '.join(src)}) : {STATUT_LONG.get(st, st)}." + ("" if len(src) >= 2 else " Une seule source : à confirmer."))
                r["statut"] = st
                if st == "NC" and not r.get("recommandation") and k in RECOS:
                    r["recommandation"] = f"Sur {nom} : " + RECOS[k]
    # baromètre e-mail : statut retenu par la lecture critique, puis critères « non testé » tranchés par des sources concordantes
    import re as _re
    ORD = ["NC", "C", "NA", "NT"]
    for compte, l in LECTURE.get("_emails", {}).items():
        crits = ETAT.get("emails", {}).get(compte, {})
        for x in l.get("ecarts", []):
            m_ = _re.match(r"Sur ([A-Z0-9-]+) ", x.get("constat", ""))
            c = crits.get(x["regle"])
            if m_ and c and m_.group(1) in c["ecrans"] and x["statut"] in ("C", "NC", "NA") and c["ecrans"][m_.group(1)][0] != x["statut"]:
                c["ecrans"][m_.group(1)] = [x["statut"], f"Lecture critique ({x['type']}) : {x['pourquoi']}"]
        for code_c, par in l.get("recoupement", {}).items():
            c = crits.get(code_c)
            if not c:
                continue
            for code, src in par.items():
                if code in c["ecrans"] and c["ecrans"][code][0] in ("NT", "I"):
                    v = {x for a, x in src.items() if a != "Checklist (script et IA)" and x in ("C", "NC")}
                    if len(v) == 1:
                        st = v.pop()
                        c["ecrans"][code] = [st, f"Tranché par les sources concordantes ({', '.join(a for a in src if a != 'Checklist (script et IA)')}) : {STATUT_LONG[st]}."]
        for c in crits.values():
            sts = [v[0] for v in c["ecrans"].values()]
            c["statut"] = next((s_ for s_ in ORD if s_ in sts), c.get("statut"))
    for nom, p in PARCOURS_RES.items():
        pa = p.get("paiement", {})
        if "cases_precochees" not in pa or nom not in ETAT.get("sites", {}):
            continue
        pre = [c for c in pa["cases_precochees"] if any(w in c.lower() for w in ("offre", "offer", "news", "e-mail", "email"))]
        ETAT["sites"][nom]["33"] = {"titre": ref["33"]["description"]["fr"], "theme": ", ".join(ref["33"]["metadata"].get("Thématiques", [])),
            "methode": "parcours", "statut": "NC" if pre else "C", "scripts": None, "robot": None, "pages_nc": ["Paiement"] if pre else [],
            "determinant": [f"Parcours réel (tranché par Claude, validé par {qui()}) : " + (f"à la page de paiement, la case « {pre[0]} » est cochée d'avance." if pre else "aucune case d'inscription cochée d'avance à la page de paiement.")],
            "sources": [{"nom": AUD["noms"]["contre_examen"].format(site=nom), "url": AUD["base"] + AUD["contre_examen"][nom], "statut": "NC" if pre else "C"}] if nom in AUD.get("contre_examen", {}) else [],
            "recommandation": (f"Sur {nom} (paiement) : " + recos["33"]) if pre else ""}


STATUT_LONG = {"C": "conforme", "NC": "non conforme", "NA": "non applicable"}


def exemple(code) -> str:
    ex = EXEMPLES.get(str(code))
    if not ex:
        return ""
    return (f'<details class="ex"><summary>Exemple clé en main</summary><pre>{e(ex)}</pre>'
            '<button type="button" class="copier">Copier</button></details>')


def reco(texte: str, code) -> str:
    return (e(texte) + exemple(code)) if texte else ""


def acc(titre: str, resume: str, corps: str, ouvert: bool = False, ident: str = "") -> str:
    return (f'<details class="acc"{f' id="{ident}"' if ident else ""}{" open" if ouvert else ""}><summary><span class="acc-t">{titre}</span>'
            f'<span class="acc-r">{resume}</span></summary><div class="acc-body">{corps}</div></details>')


TYPE_PASTILLE = {"faux positif": ("attention", "faux positif"), "faux négatif": ("non-conforme", "faux négatif"),
                 "écart à vérifier": ("afaire", "écart à vérifier"), "divergence de critère": ("afaire", "à trancher"),
                 "inattendu pertinent": ("info", "inattendu, pertinent"), "limite d'outil": ("info", "limite d'outil"),
                 "écart": ("afaire", "écart")}
AUD: dict = {}
RECOS: dict = {}
METH: dict = {}
RAISON: dict = {}
EXCLUSIONS: dict = {}


def url_audit(typ: str, nom: str) -> str:
    """Adresse de l'audit eServices Manager d'un site (referentiel/audits-esm.json), vide s'il n'y est pas."""
    return AUD.get("base", "") + AUD[typ][nom] if nom in AUD.get(typ, {}) else ""


def lien(nom: str, url: str) -> str:
    ext = url.startswith("http")
    return f'<a href="{e(url)}"' + (' target="_blank" rel="noopener"' if ext else ' class="ancre"') + f'>{e(nom)}</a>'


def liens_ecart(x: dict, nom: str, sid: str) -> str:
    """Liens vers l'audit (ou les audits) d'où vient chaque écart."""
    basics = ("Opquast basics (robot)", url_audit("basics", nom))
    scripts = ("Opquast scripts sans IA", url_audit("scripts", nom))
    ce, cep = (source_ce(), url_audit("contre_examen", nom)), (f"Contre-examen et parcours (validé par {qui()})", url_audit("contre_examen", nom))
    nu_acc = next(iter(OUTILS_LIGNE.get(nom, {}).get("nu", {}).values()), {}).get("details_url", "")
    m = {"robot / scripts": [basics, scripts],
         "robot / contre-examen navigateur": [basics, ce],
         "nos outils entre eux": [scripts, ("Validateur Nu", nu_acc or f"#{sid}-nu")],
         "eServices Manager": [scripts],
         "relevé navigateur": [("Traceurs avant consentement", f"#{sid}-traceurs")],
         "validateur Nu": [("Validateur Nu", f"#{sid}-nu")],
         "parcours réel (paiement)": [cep],
         "Lighthouse / IBM Equal Access / axe-core": [("Lighthouse", f"#{sid}-lighthouse"), ("IBM Equal Access", f"#{sid}-ibm"), ("axe-core", f"#{sid}-axe")]}
    par_audit = {"Opquast basics (robot)": basics, source_ce(): ce, "Parcours réel": cep,
                 "axe-core": ("axe-core", f"#{sid}-axe"), "IBM Equal Access": ("IBM Equal Access", f"#{sid}-ibm"),
                 "Validateur Nu (W3C)": ("Validateur Nu", f"#{sid}-nu"), "Lighthouse accessibilité": ("Lighthouse", f"#{sid}-lighthouse"),
                 "Traceurs avant consentement": ("Traceurs avant consentement", f"#{sid}-traceurs")}
    liens = []
    for a, _ in x.get("base", []):
        cible = scripts if a.startswith(("Script", "Opquast scripts", "W3C i18n", "REDbot")) else par_audit.get(a)
        if cible and cible not in liens:
            liens.append(cible)
    for c in m.get(x["entre"], []):
        if c not in liens:
            liens.append(c)
    return " · ".join(lien(n, u) for n, u in liens if u)


def bloc_lecture(nom: str, sid: str) -> tuple[str, str]:
    l = LECTURE.get(nom)
    if not l:
        return "", "à faire"
    def statut(x):
        return pastille(DECISION_PASTILLE.get(x["statut"], "info"), x["statut_lib"]) if x["statut"] else "-"
    def base(x):
        if not x.get("base"):
            return "-"
        return "<br>".join(f'{e(a)} : ' + (pastille(DECISION_PASTILLE[v]) if v in DECISION_PASTILLE else e(v or "non mesuré")) for a, v in x["base"])
    def carte(x):
        cls, lib = TYPE_PASTILLE.get(x["type"], ("info", x["type"]))
        return (f'<div class="carte">{pastille(cls, lib)}<h4>{"Règle " + e(x["regle"]) + " : " if x["regle"][0].isdigit() else ""}{e(x["titre"])}</h4>'
                f'<p><strong>Statut de départ.</strong> {base(x)}</p>'
                f'<p><strong>Constat.</strong> {e(x["constat"])}</p><p><strong>Pourquoi.</strong> {e(x["pourquoi"])}</p>'
                f'<p><strong>Que faire.</strong> {reco(x["recommandation"], x["regle"])}</p>'
                f'<p><strong>Statut à retenir.</strong> {statut(x)}{" " + pastille("afaire", f"à arbitrer par {qui()}") if x.get("a_arbitrer") else ""}</p><p><strong>Audit.</strong> {liens_ecart(x, nom, sid) or "-"}</p></div>')
    o = ['<p class="note">Les 3 résultats les plus intéressants d\'abord. Pour chaque écart : le constat, pourquoi c\'est un faux positif, '
         'un faux négatif ou autre chose, ce qu\'il faut faire, et le statut à retenir dans le baromètre. '
         f'Sur les règles mesurées à la fois par le robot et nos scripts, ils sont d\'accord {l["accords_robot_scripts"]} fois.</p>',
         '<h4>Les 3 résultats intéressants</h4><div class="trois">' + "".join(carte(x) for x in l["trois_interessants"]) + '</div>']
    autres = [x for x in l["ecarts"] if x not in l["trois_interessants"]]
    if autres:
        o.append(f'<h4>Les {len(autres)} autres écarts</h4><div class="trois">' + "".join(carte(x) for x in autres) + '</div>')
    fp = sum(1 for x in l["ecarts"] if x["type"] == "faux positif"); fn = sum(1 for x in l["ecarts"] if x["type"] == "faux négatif")
    return "\n".join(o), f"{fp} faux positif(s), {fn} faux négatif(s), {len(l['ecarts'])} écarts"


DECISION_PASTILLE = {"C": "conforme", "NC": "non-conforme", "NA": "non-applicable", "NT": "non-testé"}


def bloc_contre_examen(nom: str) -> tuple[str, str]:
    lignes = FICHE.get(nom, [])
    if not lignes:
        return "", "à faire"
    o = ['<p class="note">Les règles du socle Opquast basics qu\'aucun script ne peut trancher (hors règles retirées : compte, commande ou envoi réel) : verdict du robot, constat relevé dans le navigateur, '
         f'puis décision <strong>tranchée par Claude, à valider par {e(qui())}</strong> ; « parcours de {e(qui())} » quand il faut un compte, une commande ou un envoi. '
         f'Saisi dans eServices Manager avec la règle 33 : {lien(AUD["noms"]["contre_examen"].format(site=nom), url_audit("contre_examen", nom))}.</p>',
         '<div class="tbl"><table class="compact"><thead><tr><th>N°</th><th>Règle</th><th>Robot</th><th>Constat dans le navigateur</th><th>Décision</th><th>Recommandation</th></tr></thead><tbody>']
    n_dec = 0
    for x in lignes:
        d = x.get("decision_statut")
        n_dec += bool(d)
        dec = (pastille(DECISION_PASTILLE[d]) + f'<br><small>{e(x.get("decision_motif", ""))}</small>') if d else pastille("afaire", f"parcours de {qui()}") + f'<br><small>{e(x.get("decision_motif", ""))}</small>'
        rob = pastille(DECISION_PASTILLE.get(x["robot"], "non-testé")) if x["robot"] else "-"
        rc = f'<br><small>{e(x["robot_constat"][:200])}</small>' if x.get("robot_constat") else ""
        rec = reco(ETAT.get("sites", {}).get(nom, {}).get(str(x["regle"]), {}).get("recommandation", ""), x["regle"]) if d in ("NC", None) else ""
        o.append(f'<tr><td class="num">{x["regle"]}</td><td>{e(x["titre"])}</td><td>{rob}{rc}</td><td>{e(x["constat_navigateur"])}</td><td>{dec}</td><td>{rec}</td></tr>')
    o.append('</tbody></table></div>')
    return "\n".join(o), f"{n_dec} sur {len(lignes)} tranchées"


def bloc_parcours(nom: str) -> str:
    p = PARCOURS_RES.get(nom)
    if not p:
        return ""
    o = ['<h4>Parcours réels (sans commande, sans compte, sans envoi)</h4><ul class="items">']
    if p.get("erreur"):
        o.append(f'<li>Parcours interrompu : {e(p["erreur"])}</li>')
    k = p.get("clavier_accueil")
    if k:
        o.append(f'<li><strong>Clavier, accueil (165, 166).</strong> {k["elements_atteints"]} éléments atteints en {k["tabulations"]} tabulations, '
                 f'{k["sans_indicateur"]} sans contour ni ombre de focus.</li>')
    kp = p.get("clavier_produit")
    if kp:
        t = kp["bouton_panier_atteint_en_tabulations"]
        o.append('<li><strong>Clavier, fiche produit (166).</strong> ' + (f'« Ajouter au panier » atteint en {t} tabulations ; ajout au clavier {"réussi" if kp["ajout_au_clavier"] else "sans effet (taille à choisir ?)"}.' if t else '« Ajouter au panier » non atteint en 80 tabulations. ' + reco("Recommandation : " + RECOS.get("166", ""), "166")) + '</li>')
    f = p.get("formulaire")
    if f and f.get("trouve"):
        o.append('<li><strong>Newsletter, adresse « test@ » sans envoi (79, 80).</strong> ' + (
            'Le site gère ses propres messages (novalidate) : à vérifier à l\'envoi. ' + reco("Recommandation : " + RECOS.get("80", ""), "80") if f.get("message_propre_au_site") else
            (f'Refusée avant envoi, message du navigateur : « {e(f["message_navigateur"])} ».' if not f["valide"] else 'Acceptée sans vérification.')) + '</li>')
    pa = p.get("paiement", {})
    if pa and not pa.get("non_teste"):
        o.append('<li><strong>Commande sans compte (30).</strong> ' + ("Possible." if not pa["connexion_obligatoire"] else "Connexion exigée.") + '</li>')
        o.append(f'<li><strong>Moyens de paiement (58).</strong> {e(", ".join(pa["moyens_paiement"]))}.</li>')
        o.append('<li><strong>Étapes (87).</strong> ' + (e(" > ".join(pa["etapes"])) if pa["etapes"] else "Paiement sur une seule page, sans liste d'étapes. " + reco("Recommandation : " + RECOS.get("87", ""), "87")) + '</li>')
        pre = [c for c in pa.get("cases_precochees", []) if any(w in c.lower() for w in ("offre", "offer", "news", "e-mail", "email"))]
        o.append('<li><strong>Cases cochées d\'avance (33).</strong> ' + (f'« {e(pre[0])} » : inscription aux offres activée par défaut. ' + reco("Recommandation : " + RECOS.get("33", ""), "33") if pre else "Aucune inscription cochée d'avance.") + '</li>')
    o.append('</ul>')
    return "\n".join(o)


# --- les composants du baromètre des sites, dans l'ordre -------------------------------------------------
def _pages(nom):
    return {u: p for u, p in OUTILS_PAGES.get(nom, {}).get("pages", {}).items() if not p.get("non_teste")}


def comp_scripts(nom, regles):
    sc = [v["scripts"] for v in regles.values() if v["scripts"] in ("C", "NC")]
    return (f'{sc.count("C")} conformes, {sc.count("NC")} non conformes', "ok", url_audit("scripts", nom))


def comp_basics(nom, regles):
    v = COMPLEMENTS.get("scores_basics", {}).get(nom)  # score relevé dans eServices Manager (compléments optionnels)
    return (f"score {v:.1f} %".replace(".", ",") if v is not None else "score -", "ok", url_audit("basics", nom))


def comp_ce(nom, regles):
    f = FICHE.get(nom, [])
    d = [x for x in f if x.get("decision_statut")]
    if not f:
        return ("à faire", "afaire", "")
    return (f'{len(d)} / {len(f)} tranchées (à valider par {qui()}), {sum(1 for x in d if x["decision_statut"] == "NC")} non conformes', "attention", url_audit("contre_examen", nom))


def comp_axe(nom, regles):
    a = AXE.get("sites", {}).get(nom)
    return (f'{a["regles_en_violation"]} règles en défaut (à relancer)', "attention", "") if a else ("à faire", "afaire", "")


def comp_ibm(nom, regles):
    v = [p["ibm"]["violations"] for p in _pages(nom).values() if p.get("ibm")]
    return (f'{min(v)} à {max(v)} violations par page', "ok", "") if v else ("à faire", "afaire", "")


def comp_lh(nom, regles):
    v = [p["lighthouse"] for p in _pages(nom).values() if p.get("lighthouse", {}).get("performance") is not None]
    if not v:
        return ("en cours", "afaire", "")
    return (f'performance {min(x["performance"] for x in v)} à {max(x["performance"] for x in v)}, accessibilité {min(x["accessibilite"] for x in v)} à {max(x["accessibilite"] for x in v)}', "ok" if len(v) >= 4 else "attention", "")


def comp_eco(nom, regles):
    from collections import Counter
    v = [p["ecoindex"]["note"] for p in _pages(nom).values() if p.get("ecoindex")]
    return ("notes " + ", ".join(f"{k} x {n}" for k, n in sorted(Counter(v).items())), "ok", "") if v else ("à faire", "afaire", "")


def comp_nu(nom, regles):
    v = [x["erreurs"] for x in OUTILS_LIGNE.get(nom, {}).get("nu", {}).values() if "erreurs" in x]
    t = len(OUTILS_LIGNE.get(nom, {}).get("nu", {}))
    return (f'{min(v)} à {max(v)} erreurs ({len(v)} pages sur {t})', "ok" if len(v) == t else "attention", "") if v else ("à faire", "afaire", "")


def comp_obs(nom, regles):
    o = OUTILS_LIGNE.get(nom, {}).get("observatory", {})
    return ((f'note brute {o["grade"]} ({o["score"]}/100), corrigée {o["score_corrige"]}/100' if "score_corrige" in o else f'note {o["grade"]} ({o["score"]}/100)'), "ok", o["details_url"]) if o.get("grade") else ("à faire", "afaire", "")


def comp_ssl(nom, regles):
    s = OUTILS_LIGNE.get(nom, {}).get("ssllabs", {})
    return (f'note {", ".join(s["notes"])}', "ok", s["details_url"]) if s.get("notes") else ("à faire", "afaire", "")


def comp_trac(nom, regles):
    t = OUTILS_PAGES.get(nom, {}).get("traceurs", {})
    return (f'{t["cookies_avant_consentement"]} cookies avant consentement, dont {len(t["cookies_de_mesure"])} de mesure', "ok", "") if t.get("cookies_avant_consentement") is not None else ("à faire", "afaire", "")


def comp_ecart(nom, regles):
    return (f"{sum(1 for x in METH.values() if x == 'écartée') + len(EXCLUSIONS.get(nom, []))} règles écartées", "afaire", "")


# --- scores sur 100 ---------------------------------------------------------------------------------------
NOTES_SSL = {"A+": 100, "A": 95, "A-": 90, "B": 80, "C": 70, "D": 60, "E": 50, "F": 40, "T": 0, "M": 0}
# Un seul objectif (décision du 12/11) : la conformité Opquast. Plus de familles pondérées ; les autres outils sont des
# preuves qui aident à trancher les règles Opquast, leurs chiffres sont affichés mais ne comptent pas dans le score.
FAMILLES: list = []
AUDITS_SCORES = ("opquast", "opquast-scripts", "opquast-basics", "contre-examen")
METHODE_SCORES = [
    ("Score du baromètre", "taux de conformité Opquast : règles conformes / (conformes + non conformes), toutes sources réunies après lecture critique (scripts, robot, contre-examen, outils de recoupement)"),
    ("Audit « scripts sans IA »", "même calcul sur les seules règles mesurées par nos scripts"),
    ("Audit « Opquast basics » (robot)", "score affiché par eServices Manager"),
    ("Contre-examen et parcours", "même calcul sur les règles tranchées dans le navigateur"),
    ("Autres outils (axe-core, IBM, Pa11y, Lighthouse, Nu, W3C i18n, REDbot, SSL Labs, Observatory, sitemap)", "pas de score propre : ils servent de preuves pour trancher les règles Opquast qu'ils recoupent, et à repérer les faux positifs et faux négatifs"),
    ("Contexte (note EcoIndex, score de performance Lighthouse, traceurs avant consentement)", "affiché pour information, hors score : aucune règle Opquast mesurée ne leur correspond"),
]
GRADES = [(90, "A"), (80, "B"), (65, "C"), (50, "D"), (0, "E")]


def note_lettre(s):
    return next(l for seuil, l in GRADES if s >= seuil) if s is not None else "-"


def _taux(sts):
    c, nc = sts.count("C"), sts.count("NC")
    return round(100 * c / (c + nc)) if c + nc else None


def scores_site(nom: str) -> dict:
    regles = ETAT.get("sites", {}).get(nom, {})
    pages = _pages(nom)
    sc = {}
    sc["opquast"] = _taux([v["statut"] for v in regles.values()])
    sc["opquast-scripts"] = _taux([v["scripts"] for v in regles.values() if v["scripts"]])
    b = COMPLEMENTS.get("scores_basics", {}).get(nom)
    sc["opquast-basics"] = round(b) if b is not None else None
    sc["contre-examen"] = _taux([x.get("decision_statut") for x in FICHE.get(nom, []) if x.get("decision_statut")])
    a = AXE.get("sites", {}).get(nom)
    if a:
        v = [p["regles_respectees"] / (p["regles_respectees"] + len(p["violations"])) for p in a["pages"] if p.get("teste")]
        sc["axe"] = round(100 * sum(v) / len(v)) if v else None
    ib = [p["ibm"]["regles"] for p in pages.values() if p.get("ibm")]
    sc["ibm"] = round(sum(max(0, 100 - 5 * x) for x in ib) / len(ib)) if ib else None
    lh = [p["lighthouse"] for p in pages.values() if p.get("lighthouse", {}).get("performance") is not None]
    sc["lighthouse"] = round(sum((x["performance"] + x["accessibilite"] + x["bonnes_pratiques"] + x["seo"]) / 4 for x in lh) / len(lh)) if lh else None
    eco = [p["ecoindex"]["score"] for p in pages.values() if p.get("ecoindex")]
    sc["ecoindex"] = round(sum(eco) / len(eco)) if eco else None
    nu = [x["erreurs"] for x in OUTILS_LIGNE.get(nom, {}).get("nu", {}).values() if "erreurs" in x]
    sc["nu"] = round(100 * sum(1 for x in nu if x == 0) / len(nu)) if nu else None
    s = OUTILS_LIGNE.get(nom, {}).get("ssllabs", {})
    sc["ssllabs"] = min(NOTES_SSL.get(n, 0) for n in s["notes"]) if s.get("notes") else None
    t = OUTILS_PAGES.get(nom, {}).get("traceurs", {})
    sc["traceurs"] = max(0, 100 - 25 * len(t["cookies_de_mesure"])) if t.get("cookies_de_mesure") is not None else None
    fam = {}
    for k, lib, poids, comps in FAMILLES:
        v = [sc[c] for c in comps if sc.get(c) is not None]
        fam[k] = round(sum(v) / len(v)) if v else None
    sc["familles"] = fam
    sc["global"] = sc["opquast"]
    return sc


def score_email(compte: str) -> dict:
    crits = ETAT.get("emails", {}).get(compte, {})
    s = _taux([v["statut"] for v in crits.values()])
    return {"checklist": s, "global": s}


def pastille_score(s, petit=False) -> str:
    if s is None:
        return pastille("afaire", "à faire")
    cls = "ok" if s >= 80 else "attention" if s >= 50 else "non-conforme"
    return pastille(cls, f"{s} / 100" + ("" if petit else f" ({note_lettre(s)})"))


def bloc_methode_scores() -> str:
    lignes = "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td></tr>" for a, b in METHODE_SCORES)
    return acc("Comment le score est calculé", "un seul objectif : la conformité Opquast",
               '<p class="note">Le baromètre a un seul objectif de contrôle : la conformité des sites aux règles Opquast V5. '
               'Le score est donc le taux de conformité Opquast. Tous les autres outils servent à trancher ces règles et à repérer '
               'les faux positifs et faux négatifs ; leurs chiffres sont affichés, sans entrer dans le score. '
               'Note : A dès 90, B dès 80, C dès 65, D dès 50, E en dessous.</p>'
               f'<div class="tbl"><table class="compact"><thead><tr><th>Élément</th><th>Calcul</th></tr></thead><tbody>{lignes}</tbody></table></div>')


def exporter_scores(sites: list) -> None:
    import csv
    d = RACINE / "resultats" / f"scores-{date.today():%Y-%m-%d}"
    d.mkdir(parents=True, exist_ok=True)
    tout = {n: scores_site(n) for n in sites}
    for compte in ETAT.get("emails", {}):
        tout[compte] = score_email(compte)
    (d / "scores.json").write_text(json.dumps(tout, ensure_ascii=False, indent=1), encoding="utf-8")
    with (d / "scores.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["service", "audit", "score_sur_100", "note"])
        for n, sc in tout.items():
            for k, v in sc.items():
                if k not in AUDITS_SCORES + ("global", "checklist"):
                    continue
                else:
                    w.writerow([n, k, "" if v is None else v, note_lettre(v)])


OUTILS_RECOUP = [  # (clé, source dans la lecture critique, nom affiché, ce qu'il recoupe)
    ("axe", "axe-core", "axe-core", "accessibilité : 69, 118, 136, 182, 193"),
    ("ibm", "IBM Equal Access", "IBM Equal Access", "accessibilité : 69, 118, 136, 182, 186, 236"),
    ("pa11y", "Pa11y (HTML_CodeSniffer)", "Pa11y (HTML_CodeSniffer)", "accessibilité : 69, 117, 118, 136, 182, 236"),
    ("lighthouse", "Lighthouse", "Lighthouse (audits)", "3, 69, 118, 119, 136, 182, 193, 197, 226, 227, 229, 230"),
    ("nu", "Validateur Nu (W3C)", "Validateur Nu (W3C)", "236 (identifiants en double)"),
    ("i18n", "W3C i18n Checker", "W3C i18n Checker", "130, 228, 232, 233"),
    ("redbot", "REDbot", "REDbot", "en-têtes HTTP : 224 à 231"),
    ("ssllabs", "Qualys SSL Labs", "Qualys SSL Labs", "197, 198"),
    ("observatory", "MDN HTTP Observatory", "MDN HTTP Observatory", "199, 211, 212"),
    ("sitemap", "Sitemap (xmllint)", "Sitemap (xmllint)", "220"),
]


def comp_outil(src):
    def f(nom, regles):
        rec = LECTURE.get(nom, {}).get("recoupement", {})
        n = sum(1 for v in rec.values() if v.get(src) in ("C", "NC"))
        if not n:
            return ("à faire", "afaire", "")
        ec = sum(1 for k, v in rec.items() if v.get(src) in ("C", "NC") and {x for x in v.values() if x in ("C", "NC")} == {"C", "NC"})
        return (f"{n} règle(s) recoupée(s), {ec} écart(s) avec une autre source", "ok", "")
    return f


# (clé, nom, type, ce qu'il mesure, fonction)
COMPOSANTS = [
    ("opquast-scripts", "Opquast, scripts sans IA", "déterministe", "82 règles Opquast : en-têtes réseau, code des pages, W3C i18n, REDbot", comp_scripts),
    ("opquast-basics", "Opquast basics, robot d'eServices Manager", "probabiliste (IA)", "65 règles du socle Opquast basics, page par page", comp_basics),
    ("contre-examen", "Contre-examen et parcours réels", "manuel", "20 règles basics qu'aucun script ne tranche, vérifiées dans le navigateur, et la règle 33", comp_ce),
] + [(k, nom_, "recoupement", "règles Opquast " + quoi, comp_outil(src)) for k, src, nom_, quoi in OUTILS_RECOUP] + [
    ("ecartees", "Règles Opquast écartées", "à faire", "137 règles (jugement visuel, ou parcours impossible sans compte, commande ou envoi réel)", comp_ecart),
]


IBM_FR = {
    "aria_content_in_landmark": ("Contenu hors des repères de page", "Placer tout le contenu dans header, main, footer ou un repère nommé (bandeau d'annonce, popups compris)."),
    "svg_graphics_labelled": ("Icônes SVG sans nom", "Donner role=\"img\" et aria-label aux SVG porteurs de sens, aria-hidden=\"true\" aux SVG décoratifs."),
    "aria_id_unique": ("Identifiants en double", "Rendre uniques les id des sections répétées (section.id, forloop.index)."),
    "aria_role_valid": ("Rôle ARIA non valide", "Retirer ou corriger les attributs role inconnus ou mal placés."),
    "label_name_visible": ("Nom accessible différent du texte visible", "Faire commencer l'aria-label par le texte visible du bouton ou du lien."),
    "aria_region_labelled": ("Région sans nom", "Donner un aria-label à chaque élément role=\"region\" ou <section> nommée."),
    "aria_form_label_unique": ("Formulaires de même nom", "Donner un nom distinct à chaque formulaire (recherche en-tête, recherche page, newsletter)."),
    "aria_landmark_name_unique": ("Repères de même nom", "Nommer différemment les repères de même type (deux <nav> : « Menu principal », « Pied de page »)."),
    "input_label_after": ("Étiquette mal placée", "Placer l'étiquette avant le champ texte (après seulement pour cases et boutons radio)."),
    "input_label_before": ("Étiquette mal placée", "Placer l'étiquette après la case à cocher ou le bouton radio."),
    "aria_attribute_valid": ("Attribut ARIA non autorisé", "Retirer les attributs ARIA non autorisés pour le rôle de l'élément."),
    "element_tabbable_role_valid": ("Élément focalisable sans rôle interactif", "Donner un rôle interactif (button, link) aux éléments atteignables au clavier, ou retirer leur tabindex."),
    "aria_hidden_nontabbable": ("Contenu masqué mais focalisable", "Ajouter inert aux contenus aria-hidden (diapositives masquées, tiroirs fermés)."),
    "target_spacing_sufficient": ("Cibles tactiles trop petites ou trop serrées", "Porter les zones cliquables à 24 x 24 px au moins, idéalement 44 x 44 px."),
    "input_label_exists": ("Champ sans étiquette", "Associer une étiquette à chaque champ (label for ou aria-label)."),
    "a_text_purpose": ("Lien sans texte", "Donner un texte ou un aria-label à chaque lien."),
    "label_ref_valid": ("Étiquette qui pointe vers un id absent", "Corriger l'attribut for de l'étiquette pour qu'il corresponde à l'id du champ."),
    "text_contrast_sufficient": ("Contraste insuffisant", "Foncer le texte pour atteindre 4,5:1 (3:1 au-delà de 24 px)."),
    "img_alt_redundant": ("Alternative redondante", "Ne pas répéter dans l'alt le texte déjà présent à côté de l'image (alt=\"\" dans ce cas)."),
    "fieldset_label_valid": ("Groupe de champs sans légende", "Donner une <legend> à chaque <fieldset> (taille, couleur)."),
    "input_checkboxes_grouped": ("Cases à cocher non groupées", "Regrouper les cases liées dans un <fieldset> avec <legend> (filtres de collection)."),
    "img_alt_valid": ("Image sans alternative valide", "Ajouter un alt à chaque image (vide si décorative)."),
    "label_content_exists": ("Étiquette vide", "Écrire un texte dans chaque <label>."),
    "aria_main_label_unique": ("Plusieurs zones principales", "Ne garder qu'un seul <main> par page."),
    "aria_navigation_label_unique": ("Menus de même nom", "Nommer chaque <nav> différemment avec aria-label."),
}
NU_FR = [
    ("Duplicate ID", "Identifiants en double", "Rendre uniques les id des sections répétées.", "236"),
    ("No space between attributes", "Attributs collés", "Séparer les attributs par un espace et entourer chaque valeur Liquid de guillemets.", "nu"),
    ("Duplicate attribute", "Attribut répété", "Ne déclarer chaque attribut qu'une fois par balise (souvent class ou style ajoutés deux fois).", "nu"),
    ("Bad value", "Valeur d'attribut invalide", "Corriger les valeurs signalées (width en pixels sans « px », URL avec espaces, rel inconnu).", "nu"),
    ("Style rule", "CSS invalide dans la page", "Corriger les règles CSS signalées dans les balises <style> du thème ou des applications.", "nu"),
    ("Element", "Élément mal placé", "Corriger l'imbrication signalée (div dans un bouton, li hors d'une liste, élément interdit à cet endroit).", "nu"),
    ("Attribute", "Attribut non autorisé", "Retirer les attributs non autorisés sur l'élément, ou les préfixer en data-.", "nu"),
    ("An", "Structure invalide", "Ouvrir le rapport : le plus souvent un élément sans attribut obligatoire (img sans alt, source sans type).", "nu"),
    ("The", "Usage déconseillé", "Ouvrir le rapport : attributs ou éléments obsolètes à remplacer (type sur script, frameborder sur iframe).", "nu"),
    ("A", "Structure invalide", "Ouvrir le rapport et corriger la balise signalée.", "nu"),
    ("When the", "Règle d'usage", "Ouvrir le rapport et corriger la balise signalée.", "nu"),
]


def reco_nu(message: str) -> tuple[str, str, str]:
    for pref, fr, rec, code in NU_FR:
        if message.startswith(pref):
            return fr, rec, code
    return message, "Ouvrir le rapport et corriger la balise signalée.", "nu"


def reco_lighthouse(lh: dict) -> str:
    r = []
    if lh["lcp_s"] > 2.5:
        r.append(f"LCP {lh['lcp_s']} s (cible 2,5 s) : précharger l'image principale et la servir à la bonne taille")
    if lh["tbt_ms"] > 300:
        r.append(f"TBT {lh['tbt_ms']} ms (cible 200 ms) : différer ou retirer les scripts d'applications tierces")
    if lh["cls"] > 0.1:
        r.append(f"CLS {lh['cls']} (cible 0,1) : fixer largeur et hauteur des images et des bandeaux")
    if lh["bonnes_pratiques"] < 90:
        r.append("bonnes pratiques : corriger les erreurs de la console et les cookies tiers")
    if lh["accessibilite"] < 90:
        r.append("accessibilité : voir axe-core")
    if lh["seo"] < 90:
        r.append("SEO : meta description et liens explicites")
    return "; ".join(r) + "." if r else "Rien de prioritaire."


def reco_eco(ec: dict) -> str:
    r = []
    if ec["dom"] > 1500:
        r.append(f"{ec['dom']} éléments (repère 600) : alléger menus, carrousels et sections cachées")
    if ec["requetes"] > 100:
        r.append(f"{ec['requetes']} requêtes (repère 40) : retirer les applications et scripts inutiles")
    if ec["poids_ko"] > 3000:
        r.append(f"{ec['poids_ko'] / 1024:.1f} Mo (repère 1 Mo) : images à la bonne taille, vidéo remplacée par une image")
    return "; ".join(r) + "." if r else "Rien de prioritaire."


# --- graphiques (SVG en ligne, sans bibliothèque) --------------------------------------------------------
def svg_barres(lignes: list, vmax: float, titre: str, unite: str = "", label_w: int = 128) -> str:
    """Barres horizontales, une seule série. lignes : (libellé, valeur, texte de valeur)."""
    if not lignes:
        return ""
    h, larg, x0 = 24, 420, label_w
    zone = larg - x0 - 78
    o = [f'<figure class="viz"><figcaption>{e(titre)}</figcaption><svg viewBox="0 0 {larg} {len(lignes) * h + 6}" role="img" aria-label="{e(titre)}">']
    for i, (lib, v, txt) in enumerate(lignes):
        y = i * h + 4
        w = max(2, zone * (v / vmax if vmax else 0))
        o.append(f'<g><title>{e(lib)} : {e(txt)}</title><text x="{x0 - 8}" y="{y + 14}" text-anchor="end" class="v-lab">{e(lib[:20])}</text>'
                 f'<rect x="{x0}" y="{y + 3}" width="{zone}" height="14" class="v-track" rx="3"/>'
                 f'<rect x="{x0}" y="{y + 3}" width="{w:.1f}" height="14" class="v-bar" rx="3"/>'
                 f'<text x="{x0 + w + 6:.1f}" y="{y + 14}" class="v-val">{e(txt)}</text></g>')
    o.append('</svg></figure>')
    return "".join(o)


STATUTS_VIZ = [("C", "conformes", "v-c"), ("NC", "non conformes", "v-nc"), ("NT", "à trancher", "v-nt"), ("NA", "non applicables", "v-na"), ("AF", "à faire", "v-af")]


def svg_empile(lignes: list, titre: str, label_w: int = 128) -> str:
    """Barres empilées des statuts Opquast. lignes : (libellé, {statut: nombre})."""
    larg = 420
    zone = larg - label_w - 44
    h = 28
    tot_leg = {k: sum(d.get(k, 0) for _, d in lignes) for k, _, _ in STATUTS_VIZ}
    o = [f'<figure class="viz"><figcaption>{e(titre)}</figcaption><ul class="v-leg">'
         + "".join(f'<li><i class="{c}"></i>{e(l)}' + (f" ({tot_leg[k]})" if len(lignes) == 1 else "") + '</li>' for k, l, c in STATUTS_VIZ)
         + f'</ul><svg viewBox="0 0 {larg} {len(lignes) * h + 4}" role="img" aria-label="{e(titre)}">']
    for i, (lib, d) in enumerate(lignes):
        y = i * h + 4
        tot = sum(d.values()) or 1
        x = label_w
        o.append(f'<text x="{label_w - 8}" y="{y + 14}" text-anchor="end" class="v-lab">{e(lib[:20])}</text>')
        for k, l, c in STATUTS_VIZ:
            n = d.get(k, 0)
            if not n:
                continue
            w = zone * n / tot
            o.append(f'<g><title>{e(lib)} : {n} {e(l)}</title><rect x="{x:.1f}" y="{y + 3}" width="{max(w - 2, 1):.1f}" height="16" rx="3" class="{c}"/></g>')
            x += w
        c_, nc_ = d.get("C", 0), d.get("NC", 0)
        o.append(f'<text x="{label_w + zone + 6}" y="{y + 15}" class="v-val">{100 * c_ / (c_ + nc_):.0f} %</text>' if c_ + nc_ else "")
    o.append('</svg></figure>')
    return "".join(o)


def comptes_statuts(regles: dict) -> dict:
    st = [v["statut"] for v in regles.values()]
    d = {k: st.count(k) for k in ("C", "NC", "NA")}
    d["NT"] = st.count("NT") + st.count("I")
    d["AF"] = 245 - len(regles)
    return d


def moyenne(v):
    return round(sum(v) / len(v)) if v else 0


def coup_doeil_site(nom: str, regles: dict) -> str:
    sc = scores_site(nom)
    aud = [(lib, sc[k], f"{sc[k]} %") for k, lib in (("opquast-scripts", "Scripts sans IA"), ("opquast-basics", "Robot basics"), ("contre-examen", "Contre-examen")) if sc.get(k) is not None]
    o = ['<div class="viz-grille">', svg_barres([("Score du baromètre", sc["global"], f'{sc["global"]} %, note {note_lettre(sc["global"])}')] * (sc["global"] is not None) + aud, 100, "Conformité Opquast : baromètre et audits"),
         svg_empile([("Opquast, 245 règles", comptes_statuts(regles))], "Les 245 règles Opquast, par statut")]
    o.append('</div>')
    return "".join(o)


def tableau_pages(nom: str, entetes: list[str], cellules) -> str:
    o = ['<div class="tbl"><table class="compact"><thead><tr><th>Page</th>' + "".join(f"<th>{h}</th>" for h in entetes) + '</tr></thead><tbody>']
    for url, p in OUTILS_PAGES.get(nom, {}).get("pages", {}).items():
        page = f'{e(p["gabarit"])}<br><small><a href="{e(url)}" target="_blank" rel="noopener">{e(url.split("/", 3)[-1] or "/")}</a></small>'
        if p.get("non_teste"):
            o.append(f'<tr><td>{page}</td><td colspan="{len(entetes)}"><small>Non testé : {e(p["non_teste"])}</small></td></tr>')
        else:
            o.append(f'<tr><td>{page}</td>' + "".join(f"<td>{c}</td>" for c in cellules(url, p)) + '</tr>')
    o.append('</tbody></table></div>')
    return "\n".join(o)


def bloc_ibm(nom):
    pages = _pages(nom)
    regles = {}
    for p in pages.values():
        for k, v in p.get("ibm", {}).get("par_regle", {}).items():
            r = regles.setdefault(k, [0, 0]); r[0] += v; r[1] += 1
    o = ['<p class="note">Moteur accessibility-checker-engine (open source), lancé dans le navigateur. Il compte chaque élément en défaut, d\'où des chiffres plus élevés qu\'axe-core.</p>',
         svg_barres([(p["gabarit"].split(" (")[0], p["ibm"]["violations"], str(p["ibm"]["violations"])) for p in pages.values() if p.get("ibm")],
                    max([p["ibm"]["violations"] for p in pages.values() if p.get("ibm")] or [1]), "Violations par page"),
         '<div class="tbl"><table class="compact"><thead><tr><th>Règle IBM</th><th>Problème</th><th>Éléments en défaut</th><th>Recommandation</th></tr></thead><tbody>']
    for k, (n, np_) in sorted(regles.items(), key=lambda kv: -kv[1][0]):
        fr, rec = IBM_FR.get(k, (k, "Ouvrir le rapport IBM pour le détail."))
        o.append(f'<tr><td class="num">{e(k)}</td><td>{e(fr)}</td><td>{n} sur {np_} page(s)</td><td>{reco("Sur " + nom + " : " + rec, "ibm" if k in ("svg_graphics_labelled", "aria_content_in_landmark") else k)}</td></tr>')
    o.append('</tbody></table></div>')
    return "\n".join(o)


def bloc_lighthouse(nom):
    def c(url, p):
        lh = p.get("lighthouse")
        if not lh:
            return ["<small>gabarit non mesuré</small>"] + [""] * 5
        if "performance" not in lh:
            return [f'<small>{e(lh.get("erreur", ""))[:80]}</small>'] + [""] * 5
        return [str(lh["performance"]), str(lh["accessibilite"]), str(lh["bonnes_pratiques"]), str(lh["seo"]),
                f'LCP {lh["lcp_s"]} s, CLS {lh["cls"]}, TBT {lh["tbt_ms"]} ms', reco("Sur cette page : " + reco_lighthouse(lh), "outil-lighthouse")]
    lh = [p["lighthouse"] for p in _pages(nom).values() if p.get("lighthouse", {}).get("performance") is not None]
    g = svg_barres([(lib, moyenne([x[k] for x in lh]), f"{moyenne([x[k] for x in lh])} / 100") for k, lib in
                    (("performance", "Performance"), ("accessibilite", "Accessibilité"), ("bonnes_pratiques", "Bonnes pratiques"), ("seo", "SEO"))], 100, "Moyenne des gabarits mesurés") if lh else ""
    return ('<p class="note">Lighthouse 12, bureau, sur accueil, collection, produit et panier. Scores sur 100.</p>' + g
            + tableau_pages(nom, ["Perf.", "Access.", "Bonnes pr.", "SEO", "Mesures", "Recommandation"], c))


def bloc_ecoindex(nom):
    def c(url, p):
        ec = p.get("ecoindex")
        return ([f'<strong>{ec["note"]}</strong> ({ec["score"]}/100)', str(ec["dom"]), str(ec["requetes"]), f'{ec["poids_ko"] / 1024:.1f} Mo',
                 f'{ec["ges_g"]} g CO2e, {ec["eau_cl"]} cl', reco("Sur cette page : " + reco_eco(ec), "outil-ecoindex")] if ec else ["-"] * 6)
    eco = [(p["gabarit"].split(" (")[0], p["ecoindex"]["score"], f'{p["ecoindex"]["note"]} ({p["ecoindex"]["score"]})') for p in _pages(nom).values() if p.get("ecoindex")]
    return ('<p class="note">Formule publiée de l\'EcoIndex (GreenIT), calculée sur la page défilée jusqu\'en bas. Note A (au-dessus de 80) à G (10 et moins).</p>'
            + svg_barres(eco, 100, "Score EcoIndex par page") + tableau_pages(nom, ["Note", "Éléments", "Requêtes", "Poids", "GES, eau", "Recommandation"], c))


def bloc_nu(nom):
    nu = OUTILS_LIGNE.get(nom, {}).get("nu", {})
    o = ['<p class="note">Validateur HTML du W3C (validator.w3.org/nu). Les pages « à refaire » n\'ont pas pu être testées : le service limite le nombre d\'appels.</p>',
         svg_barres([(n["gabarit"].split(" (")[0], n["erreurs"], str(n["erreurs"])) for n in nu.values() if "erreurs" in n],
                    max([n["erreurs"] for n in nu.values() if "erreurs" in n] or [1]), "Erreurs HTML par page"),
         '<div class="tbl"><table class="compact"><thead><tr><th>Page</th><th>Erreurs</th><th>Erreurs les plus fréquentes et recommandation</th></tr></thead><tbody>']
    for url, n in nu.items():
        if "erreurs" in n:
            det = "".join(f'<li><strong>{e(reco_nu(m)[0])}</strong> ({k}) : {reco(reco_nu(m)[1], reco_nu(m)[2])}</li>' for m, k in n.get("principales", [])[:4])
            o.append(f'<tr><td>{e(n["gabarit"])}</td><td><a href="{e(n["details_url"])}" target="_blank" rel="noopener">{n["erreurs"]}</a><br><small>{n["avertissements"]} avertissements</small></td>'
                     f'<td>{"<ul class=\"mini\">" + det + "</ul>" if det else "Aucune erreur."}</td></tr>')
        else:
            o.append(f'<tr><td>{e(n.get("gabarit", url))}</td><td colspan="2"><small>À refaire ({e(n.get("erreur", ""))[:40]})</small></td></tr>')
    o.append('</tbody></table></div>')
    return "\n".join(o)


def bloc_observatory(nom):
    o = OUTILS_LIGNE.get(nom, {}).get("observatory", {})
    if not o.get("grade"):
        return ""
    VERDICT = {
        "csp-implemented-with-unsafe-inline": ("CSP sans limite sur les scripts", "réel : la CSP de Shopify ne contient ni default-src ni script-src"),
        "cookies-without-secure-flag": ("Cookie sans attribut Secure", "réel : le cookie localization est posé sans Secure"),
        "hsts-implemented-max-age-less-than-six-months": ("HSTS trop court", "réel : max-age de 91 jours (règle Opquast 199)"),
        "sri-not-implemented-and-external-scripts-not-loaded-securely": ("Scripts externes non sécurisés et sans SRI", "non reproduit : dans le code des pages, tous les scripts externes sont en HTTPS et le seul en « // » porte un attribut integrity"),
        "x-frame-options-implemented-via-csp": ("Protection contre l\'intégration en iframe", "réel : frame-ancestors dans la CSP"),
    }
    lignes = "".join(f'<tr><td>{e(VERDICT.get(r, (r, ""))[0])}</td><td class="num">{m:+d}</td><td>{e(VERDICT.get(r, ("", "à vérifier"))[1])}</td></tr>' for _, r, m in o.get("penalites", []))
    return (f'<p><a href="{e(o["details_url"])}" target="_blank" rel="noopener">Note brute <strong>{o["grade"]}</strong>, {o["score"]}/100</a> : '
            f'{o["tests_passed"]} tests réussis, {o["tests_failed"]} échoués sur {o["tests_quantity"]}. '
            + (f'<strong>Score corrigé retenu dans le baromètre : {o["score_corrige"]}/100.</strong></p>' if "score_corrige" in o else '</p>')
            + '<p class="note">Observatory part de 100 et retire des points ; les bonus ne comptent qu\'au-dessus de 90. Chaque pénalité a été vérifiée sur le code et les en-têtes réels :</p>'
            + (f'<div class="tbl"><table class="compact"><thead><tr><th>Test</th><th>Points</th><th>Vérification</th></tr></thead><tbody>{lignes}</tbody></table></div>' if lignes else '')
            + f'<p class="note"><strong>Recommandation.</strong> {reco("Sur " + nom + " : allonger le HSTS à un an (règle 199), poser Secure sur tous les cookies, puis ajouter une CSP en mode Report-Only avec script-src.", "212")}</p>')


def bloc_ssl(nom):
    s = OUTILS_LIGNE.get(nom, {}).get("ssllabs", {})
    if not s.get("notes"):
        return ""
    return (f'<p><a href="{e(s["details_url"])}" target="_blank" rel="noopener">Note <strong>{", ".join(s["notes"])}</strong></a> sur {s["serveurs"]} serveur(s) : certificat et protocoles corrects.</p>'
            f'<p class="note"><strong>Recommandation.</strong> {reco("Sur " + nom + " : pour viser A+, allonger le HSTS à un an (règle 199), à demander au support Shopify.", "199")}</p>')


def bloc_traceurs(nom):
    t = OUTILS_PAGES.get(nom, {}).get("traceurs", {})
    if t.get("cookies_avant_consentement") is None:
        return ""
    return (f'<p>Accueil ouvert dans un navigateur vierge, aucun clic : <strong>{t["cookies_avant_consentement"]} cookies</strong> déposés, '
            f'dont de mesure ou marketing : {e(", ".join(t["cookies_de_mesure"]) or "aucun")}. {len(t["traceurs_connus"])} domaines de traceurs appelés : {e(", ".join(t["traceurs_connus"]))}. '
            f'Bandeau de consentement {"présent" if t.get("bandeau_consentement") else "non repéré"}.</p>'
            f'<p class="note"><strong>Recommandation.</strong> {reco("Sur " + nom + " : " + ("bloquer " + ", ".join(t["cookies_de_mesure"]) + " jusqu'au consentement." if t["cookies_de_mesure"] else "vérifier, cookie par cookie, que les appels aux domaines tiers attendent le consentement."), "outil-traceurs")}</p>')


ABR_MODELE = {"Script réseau (controles_reseau.py)": "Réseau", "Script code de la page (controles_page.js)": "Page", "W3C i18n Checker": "i18n",
       "REDbot": "REDbot", "Opquast basics (robot)": "Robot", "Contre-examen (validé par {responsable})": "Contre-ex.", "axe-core": "axe",
       "IBM Equal Access": "IBM", "Pa11y (HTML_CodeSniffer)": "Pa11y", "Lighthouse": "Lighthouse", "Validateur Nu (W3C)": "Nu",
       "Qualys SSL Labs": "SSL Labs", "MDN HTTP Observatory": "Observatory", "Sitemap (xmllint)": "Sitemap",
       # deuxièmes sources du 12/11 (plusieurs outils de même nature partagent une colonne)
       "Relevé navigateur (Claude)": "Relevé", "Playwright (événements popup)": "Fenêtres", "Chromium page.pdf + pdftotext": "PDF imprimé",
       "Shopify meta.json": "Shopify", "Shopify JSON-LD et API Ajax": "Shopify", "HTML brut et JSON-LD": "Shopify",
       "HTML brut et flux Atom Shopify": "Shopify", "HTML brut de la page 404": "Shopify", "Shopify /policies/*.json": "Shopify",
       "HTML brut (sans JavaScript)": "HTML brut", "Lecture IA indépendante (probabiliste)": "Lecture IA", "Lecture visuelle IA des captures (probabiliste)": "Captures (IA)",
       # 13/11 : outils tiers de confiance et sources complémentaires
       "Moteur Opquast devtools": "Opquast devtools", "Sa11y": "Sa11y", "Siteimprove Alfa": "Alfa", "html-validate": "html-validate",
       "Impression PDF (cookies refusés)": "PDF imprimé", "HTML brut et CSS (sans JavaScript)": "HTML brut", "curl": "curl",
       "API panier Shopify (cart.js)": "Shopify", "API panier Shopify (shipping_rates)": "Shopify", "Page de paiement (affichée)": "Paiement",
       "Lecture IA du DOM et des captures (probabiliste)": "DOM (IA)", "axe-core et IBM (aria-hidden, tableaux)": "axe"}
ABR: dict = {}


def maj_abr() -> None:
    """Colonnes courtes des sources ; la source du contre-examen porte le nom de la personne responsable."""
    ABR.clear()
    ABR.update({k.format(responsable=qui()) if "{responsable}" in k else k: v for k, v in ABR_MODELE.items()})


maj_abr()
CASE = {"C": ('<span class="cell p-done" title="conforme">C</span>'), "NC": ('<span class="cell p-block" title="non conforme">NC</span>'),
        "NA": ('<span class="cell p-na" title="non applicable">NA</span>')}


def bloc_recoupement(nom: str, sid: str, regles: dict, ref: dict) -> str:
    rec = LECTURE.get(nom, {}).get("recoupement", {})
    nsrc = LECTURE.get(nom, {}).get("sources_par_regle", {})
    cols = list(dict.fromkeys(ABR[c] for c in ABR if any(c in v for v in rec.values())))
    lignes = []
    for k in sorted(set(nsrc) or set(rec), key=lambda x: int(x) if x.isdigit() else 999):  # règles du baromètre seulement
        v = rec.get(k, {})
        par_col: dict = {}
        for src, x in v.items():
            col = ABR.get(src)
            if col and x in ("C", "NC", "NA"):
                prev = par_col.get(col)
                par_col[col] = "NC" if "NC" in (x, prev) else "C" if "C" in (x, prev) else "NA"
        vals = {x for x in par_col.values() if x in ("C", "NC")}
        ecart = vals == {"C", "NC"}
        n = max(len(par_col), len({ABR.get(a, a) for a in nsrc.get(k, [])}))  # sources concordantes en « non applicable » comprises
        st = regles.get(k, {}).get("statut")
        titre = ref[int(k)]["description"]["fr"] if k.isdigit() and int(k) in ref else k
        cells = "".join(f"<td>{CASE.get(par_col.get(c), '')}</td>" for c in cols)
        badge = f'<span class="cell {"p-done" if n >= 2 else "p-block"}" title="{n} source(s) indépendante(s)">{n}</span>'
        lignes.append((0 if ecart else 1 if n < 2 else 2, int(k) if k.isdigit() else 999, n,
                       f'<tr data-statut="{"EC" if ecart else "UN" if n < 2 else "OK"}"><td class="num">{e(k)}</td><td>{e(titre)}</td><td>{badge}</td>{cells}'
                       f'<td>{pastille(CODE_PASTILLE[st]) if st in CODE_PASTILLE else "-"}</td><td>{lien("écart", f"#{sid}-lecture") if ecart else "accord" if n >= 2 else "une seule source"}</td></tr>'))
    n_ec = sum(1 for l in lignes if l[0] == 0)
    n_un = sum(1 for l in lignes if l[2] < 2)
    n2 = len(lignes) - n_un
    return (f'<p class="note"><strong>{n2} règles sur {len(lignes)} ont au moins 2 sources</strong> ; {n_ec} présentent un écart entre sources (en tête du tableau, analysés dans la lecture critique) ; '
            f'{n_un} n\'ont encore qu\'une source (ou aucune). Colonne « Sources » : nombre de sources indépendantes qui ont tranché la règle. '
            'C = conforme, NC = non conforme, NA = non applicable selon la source ; case vide : la source ne mesure pas cette règle. '
            '« Lecture IA » est une source probabiliste (lecture des textes avec citation obligatoire) ; « HTML brut » relit le code envoyé par le serveur, sans JavaScript ; '
            '« Shopify » regroupe les données publiques de la boutique (meta.json, JSON-LD, politiques, page 404 brute).</p>'
            f'<div class="tbl"><table class="matrix"><thead><tr><th>N°</th><th>Règle</th><th>Sources</th>' + "".join(f"<th>{e(c)}</th>" for c in cols)
            + '<th>Statut retenu</th><th>Accord</th></tr></thead><tbody>' + "".join(l for _, _, _, l in sorted(lignes)) + '</tbody></table></div>')


def composition_site(s: dict, regles: dict) -> list[tuple]:
    """(clé, composant, ce qu'il mesure, résultat, état, lien)."""
    return [(k, n, quoi, *f(s["nom"], regles)) for k, n, _, quoi, f in COMPOSANTS]


def onglet(s: dict, reseau: dict) -> str:
    """Onglet d'un site : son baromètre seul (chiffres, composition, puis un accordéon par composant)."""
    if s["cat"] != "E-commerce":
        return onglet_compte_email(s)
    import csv
    nom, sid = s["nom"], s["id"]
    regles = ETAT.get("sites", {}).get(nom, {})
    ref = {r["number"]: r for r in json.loads((RACINE / "referentiel" / "opquast-checklist-v5.json").read_text(encoding="utf-8"))}
    meth = {int(x["numero"]): x["methode"] for x in csv.DictReader((RACINE / "referentiel" / "repartition-regles.csv").open(encoding="utf-8"))}
    st = [v["statut"] for v in regles.values()]
    c, nc, na, nt = (st.count(x) for x in ("C", "NC", "NA", "NT"))
    taux = f"{100 * c / (c + nc):.0f} %" if c + nc else "-"
    afaire = 245 - len(regles)
    SC = scores_site(nom)
    o = [f'<section class="tab" id="{sid}" role="tabpanel" aria-labelledby="t-{sid}" hidden>',
         f'<div class="svc-head"><div class="eyebrow">Baromètre du site</div><h2>{e(nom)}</h2><p class="lede">{e(s["version"].split(" · ")[-1])}</p></div>',
         '<section class="status" aria-label="Le baromètre en chiffres">',
         f'<div class="stat now"><b>{SC["global"] if SC["global"] is not None else "-"}<small> / 100</small></b><span>score du baromètre, note {note_lettre(SC["global"])}</span></div>',
         f'<div class="stat"><b>{taux}</b><span>de conformité Opquast sur les règles tranchées</span></div>',
         f'<div class="stat"><b>{c}</b><span>règles conformes</span></div>',
         f'<div class="stat"><b>{nc}</b><span>règles non conformes</span></div>',
         f'<div class="stat"><b>{na + nt + afaire}</b><span>non applicables, non tranchées ou à faire</span></div></section>',
         coup_doeil_site(nom, regles),
         '<h3>De quoi se compose le baromètre</h3><div class="tbl"><table class="compact"><thead><tr><th>Composant</th><th>Ce qu\'il mesure</th><th>Score</th><th>Résultat sur ce site</th><th>Audit</th></tr></thead><tbody>']
    for k, n, quoi, res, cls, url in composition_site(s, regles):
        aud = lien("ouvrir l'audit", url) if url else ""
        scr = pastille_score(SC.get(k), True) if k in AUDITS_SCORES else '<small>preuve</small>' 
        o.append(f'<tr><td><a href="#{sid}-{k}" class="ancre"><strong>{e(n)}</strong></a></td><td>{e(quoi)}</td><td>{scr}</td><td>{pastille(cls, res)}</td><td>{aud or "-"}</td></tr>')
    o.append('</tbody></table></div><p class="note">Cliquez sur un composant pour ouvrir son détail. Sous chaque recommandation, « Exemple clé en main » donne le code ou le réglage à reprendre.</p>')
    corps, res = bloc_lecture(nom, sid)
    if corps:
        o.append(acc("Lecture critique : faux positifs, faux négatifs, résultats inattendus", e(res), corps, ident=f"{sid}-lecture"))
    # Opquast : les 245 règles (scripts, robot et contre-examen réunis)
    t = [f'<p class="note">Statut de chaque règle, toutes sources réunies : {lien("audit scripts sans IA", url_audit("scripts", nom))} · {lien("audit Opquast basics (robot)", url_audit("basics", nom))}.</p>'
         f'<div class="filters"><label for="fs-{sid}">Statut</label><select id="fs-{sid}" class="f-etat" data-table="te-{sid}">'
         '<option value="">Tous</option><option value="NC">Non conformes</option><option value="C">Conformes</option>'
         '<option value="NA">Non applicables</option><option value="NT">Non tranchées</option><option value="AF">À faire</option><option value="EC">Écartées</option></select>'
         f'<span class="count" id="te-{sid}-compte" aria-live="polite"></span></div>'
         f'<div class="tbl"><table class="compact" id="te-{sid}"><thead><tr><th>N°</th><th>Critère</th><th>Statut</th><th>Résultat qui tranche</th><th>Audit</th><th>Recommandation</th></tr></thead><tbody>']
    ordre = {"NC": 0, "NT": 2, "C": 3, "NA": 4}
    lignes = []
    for n in range(1, 246):
        v = regles.get(str(n))
        r = ref[n]
        theme = ", ".join(r["metadata"].get("Thématiques", []))
        if v:
            det = "<br>".join(e(x) for x in v["determinant"])
            if v["pages_nc"]:
                det += f'<br><small>Pages non conformes : {e(", ".join(v["pages_nc"]))}</small>'
            if meth.get(n) == "manuel":
                det += f'<br><small>{lien("Voir le contre-examen", f"#{sid}-contre-examen")}</small>'
            lignes.append((ordre[v["statut"]], n, f'<tr data-statut="{v["statut"]}"><td class="num">{n}</td><td>{e(r["description"]["fr"])}<br><small>{e(theme)}</small></td>'
                          f'<td>{pastille(CODE_PASTILLE[v["statut"]])}</td><td>{det}</td><td>{liens_audits(v["sources"])}</td><td>{reco(v["recommandation"], n)}</td></tr>'))
        else:
            pourquoi = (RAISON.get(n, "Règle écartée.") if meth.get(n) == "écartée" else
                        EXCLUSIONS.get("_raisons", {}).get(str(n), EXCLUSIONS.get("_raison", "")) if n in EXCLUSIONS.get(nom, []) else "Pas encore mesurée sur ce site.")
            ec = meth.get(n) == "écartée" or n in EXCLUSIONS.get(nom, [])
            lignes.append((1 if not ec else 5, n, f'<tr data-statut="{"EC" if ec else "AF"}"><td class="num">{n}</td><td>{e(r["description"]["fr"])}<br><small>{e(theme)}</small></td>'
                          f'<td>{pastille("info", "écartée") if ec else pastille("afaire", "à faire")}</td><td><small>{e(pourquoi)}</small></td><td>-</td><td></td></tr>'))
    t += [l for _, _, l in sorted(lignes)]
    t.append('</tbody></table></div>')
    o.append("".join(f'<span id="{sid}-{k}" data-ouvre="{sid}-opquast"></span>' for k in ("opquast-scripts", "opquast-basics", "ecartees")))
    o.append(acc("Opquast : les 245 règles (scripts sans IA, robot basics, contre-examen)", f"{c} conformes, {nc} non conformes, {afaire} à faire", "\n".join(t), ident=f"{sid}-opquast"))
    corps, res = bloc_contre_examen(nom)
    cp = bloc_parcours(nom)
    if corps or cp:
        o.append(acc("Contre-examen manuel et parcours réels", e(res), corps + cp, ident=f"{sid}-contre-examen"))
    # recoupement : chaque outil, règle par règle (seuls ses résultats qui croisent une règle Opquast)
    o.append(acc("Recoupement par les outils, règle par règle", "verdict de chaque outil sur les règles Opquast qu'il recoupe", bloc_recoupement(nom, sid, regles, ref), ident=f"{sid}-recoupement"))
    for k, *_ in OUTILS_RECOUP:
        o.append(f'<span id="{sid}-{k}" data-ouvre="{sid}-recoupement"></span>')
    o.append('</section>')
    return "\n".join(o)


def onglet_compte_email(s: dict) -> str:
    import csv
    sid = s["id"]
    compte = s["nom"]
    crits = ETAT.get("emails", {}).get(compte)
    ECRANS_EMAIL = ecrans_email(compte)
    liste = list(csv.DictReader((RACINE / "referentiel" / "checklist-email.csv").open(encoding="utf-8")))
    aud = json.loads((RACINE / "referentiel" / "audits-esm.json").read_text(encoding="utf-8"))
    o = [f'<section class="tab" id="{sid}" role="tabpanel" aria-labelledby="t-{sid}" hidden>',
         f'<div class="svc-head"><div class="eyebrow">Baromètre des e-mails</div><h2>{e(s["nom"])}</h2><p class="lede">{e(s["desc"])}</p></div>']
    if crits:
        st = [v["statut"] for v in crits.values()]
        c, nc = st.count("C"), st.count("NC")
        o += ['<section class="status">',
              f'<div class="stat now"><b>{round(100 * c / (c + nc))}<small> / 100</small></b><span>score du baromètre e-mail, note {note_lettre(round(100 * c / (c + nc)))} (critères conformes / critères tranchés)</span></div>',
              f'<div class="stat"><b>{c}</b><span>critères conformes partout</span></div>',
              f'<div class="stat"><b>{nc}</b><span>critères non conformes sur au moins un écran</span></div>',
              f'<div class="stat"><b>{st.count("NA") + st.count("NT") + st.count("I")}</b><span>non applicables ou non tranchés</span></div></section>']
    url = aud["base"] + aud["email"][compte] if compte in aud.get("email", {}) else ""
    comp = [(aud["noms"]["email"].format(site=compte), f"Script sur le HTML des templates + jugement IA (Claude) : {len(liste)} critères sur {len(ECRANS_EMAIL)} écrans",
             ("ok", "fait le " + ETAT.get("date", "")) if crits else ("afaire", "à faire"), url),
            ("Tests de parcours à la main", "Désinscription en un clic, clavier, lecteur d'écran, captures en mode sombre (Gmail, Outlook, Apple Mail)", ("afaire", "à faire"), "")]
    if not crits:
        comp.insert(0, ("Accès au compte e-mail", "Connecter le compte à son connecteur (lecture seule)", ("afaire", "à faire"), ""))
    o.append('<h3>De quoi se compose le baromètre</h3><div class="tbl"><table class="compact"><thead><tr><th>Audit</th><th>Ce qu\'il mesure</th><th>État</th><th>eServices Manager</th></tr></thead><tbody>')
    for titre, quoi, (cls, lib), u in comp:
        o.append(f'<tr><td><strong>{e(titre)}</strong></td><td>{e(quoi)}</td><td>{pastille(cls, lib)}</td><td>{(f"<a href=\"{e(u)}\" target=\"_blank\" rel=\"noopener\">ouvrir l&#x27;audit</a>") if u else "-"}</td></tr>')
    o.append('</tbody></table></div>')
    o.append(f'<details class="acc"><summary><span class="acc-t">Les {len(liste)} critères de la checklist e-mail</span><span class="acc-r">statut par écran, résultat et recommandation</span></summary><div class="acc-body">'
             f'<div class="filters"><label for="fs-{sid}">Statut</label><select id="fs-{sid}" class="f-etat" data-table="te-{sid}">'
             '<option value="">Tous</option><option value="NC">Non conformes</option><option value="C">Conformes</option>'
             '<option value="NA">Non applicables</option><option value="NT">Non tranchés</option><option value="AF">À faire</option><option value="EC">Écartées</option></select>'
             f'<span class="count" id="te-{sid}-compte" aria-live="polite"></span></div>'
             f'<div class="tbl"><table class="compact" id="te-{sid}"><thead><tr><th>Critère</th><th>Intitulé</th>'
             + "".join(f'<th>{e(l)}</th>' for _, l in ECRANS_EMAIL) + '<th>Résultat qui tranche</th><th>Recommandation</th></tr></thead><tbody>')
    ordre = {"NC": 0, "I": 1, "NT": 1, "C": 2, "NA": 3}
    rows = []
    for cr in liste:
        k = cr["id"]
        v = (crits or {}).get(k)
        if not v:
            rows.append((1, k, f'<tr data-statut="AF"><td class="num">{e(k)}</td><td>{e(cr["critere"])}<br><small>{e(cr["theme"])}</small></td>'
                        + "".join(f'<td>{pastille("afaire", "à faire")}</td>' for _ in ECRANS_EMAIL) + '<td><small>Pas encore évalué.</small></td><td></td></tr>'))
            continue
        stf = "NT" if v["statut"] == "I" else v["statut"]
        cells = "".join(f'<td title="{e(v["ecrans"].get(c, ["", ""])[1])}">{pastille(CODE_PASTILLE.get(v["ecrans"].get(c, ["NT"])[0], "non-testé"))}</td>' for c, _ in ECRANS_EMAIL)
        cle = next((c for c, val in v["ecrans"].items() if val[0] == v["statut"]), None)
        det = (dict(ECRANS_EMAIL).get(cle, "") + " : " + v["ecrans"][cle][1]) if cle else ""
        lien = f'<br><small><a href="{e(v["source"]["url"])}" target="_blank" rel="noopener">{e(v["source"]["nom"])}</a></small>'
        rows.append((ordre[v["statut"]], k, f'<tr data-statut="{stf}"><td class="num">{e(k)}</td><td>{e(v["titre"])}<br><small>{e(v["theme"])}</small></td>{cells}<td>{e(det)}{lien}</td><td>{reco(v["recommandation"], k)}</td></tr>'))
    o += [r for _, _, r in sorted(rows)]
    o.append('</tbody></table></div></div></details>')
    lec = LECTURE.get("_emails", {}).get(compte)
    if lec and lec["ecarts"]:
        grp = {}
        for x in lec["ecarts"]:
            g = grp.setdefault((x["regle"], x["type"]), {**x, "ecrans": []})
            g["ecrans"].append(re.sub(r"^.*?-EM-", "", x["constat"].split(" :")[0].replace("Sur ", "")).lower())
        cartes = []
        for (crit, typ), x in grp.items():
            cls, lib = TYPE_PASTILLE.get(typ, ("info", typ))
            base = "<br>".join(f'{e(a_)} : ' + (pastille(DECISION_PASTILLE[v]) if v in DECISION_PASTILLE else e(v)) for a_, v in x["base"])
            cartes.append(f'<div class="carte">{pastille(cls, lib)}<h4>{e(crit)} : {e(x["titre"])}</h4>'
                          f'<p><strong>Écrans.</strong> {e(", ".join(x["ecrans"]))}</p><p><strong>Statut de départ.</strong> {base}</p>'
                          f'<p><strong>Constat.</strong> {e(x["constat"].split(" : ", 1)[-1])}</p><p><strong>Pourquoi.</strong> {e(x["pourquoi"])}</p>'
                          f'<p><strong>Que faire.</strong> {reco(x["recommandation"], crit)}</p><p><strong>Statut à retenir.</strong> {pastille(DECISION_PASTILLE.get(x["statut"], "info"), x["statut_lib"])}</p></div>')
        n_rec = sum(len(v) for v in lec["recoupement"].values())
        o.append(acc("Lecture critique : recoupement par axe-core et checkdmarc", f"{n_rec} résultats recoupés, {len(grp)} écart(s)",
                     '<p class="note">Seuls les résultats d\'outils qui croisent un critère de la checklist sont gardés : axe-core sur le HTML des e-mails '
                     '(EM01, EM02, EM03, EM04, EM06, EM08) et checkdmarc sur le DNS (EM25).</p><div class="trois">' + "".join(cartes) + '</div>'))
    o.append('</section>')
    return "\n".join(o)

LIBELLES_AXE = {
    "button-name": "Bouton sans nom accessible", "nested-interactive": "Éléments interactifs imbriqués",
    "link-name": "Lien sans intitulé accessible", "color-contrast": "Contraste du texte insuffisant",
    "list": "Liste mal structurée", "listitem": "Élément de liste hors d'une liste",
    "scrollable-region-focusable": "Zone défilante inaccessible au clavier", "aria-prohibited-attr": "Attribut ARIA interdit",
    "aria-hidden-focus": "Élément masqué aux lecteurs d'écran mais atteignable au clavier", "image-alt": "Image sans texte alternatif",
    "meta-viewport": "Zoom bloqué sur mobile", "label": "Champ sans étiquette", "select-name": "Liste déroulante sans nom",
    "aria-valid-attr-value": "Valeur d'attribut ARIA invalide",
}
GRAV = {"critical": "critique", "serious": "sérieuse", "moderate": "modérée", "minor": "mineure"}


AXE: dict = {}


def charger_axe() -> dict:
    fichiers = sorted(RESEAU_DIR.glob("axe-*/resultats.json"))
    return json.loads(fichiers[-1].read_text(encoding="utf-8")) if fichiers else {}


def bloc_axe(a: dict) -> str:
    o = [f'<h3>Accessibilité automatique, WCAG 2.1 A et AA</h3><p class="note">axe-core 4.10.2 dans le navigateur, {a["pages_testees"]} pages testées'
         + (f', {a["pages_non_testees"]} hors périmètre (compte client hébergé par Shopify)' if a["pages_non_testees"] else '') + '.</p>',
         '<div class="tbl"><table class="compact"><thead><tr><th>Problème</th><th>Règle axe-core</th><th>Critère WCAG</th><th>Gravité</th><th>Pages</th><th>Éléments</th></tr></thead><tbody>']
    for rid, v in sorted(a["regles"].items(), key=lambda kv: (kv[1]["gravite"] != "critical", -kv[1]["pages"])):
        cls = "ko" if v["gravite"] == "critical" else "attention"
        o.append(f'<tr><td>{e(LIBELLES_AXE.get(rid, rid))}</td><td class="tool">{e(rid)}</td><td class="num">{e(", ".join(v["criteres"]))}</td>'
                 f'<td>{pastille(cls, GRAV.get(v["gravite"], v["gravite"]))}</td><td class="num">{v["pages"]}</td><td class="num">{v["elements"]}</td></tr>')
    o.append('</tbody></table></div>')
    return "\n".join(o)


def charger_reseau() -> tuple[dict, dict]:
    """Fusionne les résultats réseau de tous les passages (le plus récent l'emporte)."""
    services, dates = {}, {}
    for f in sorted(RESEAU_DIR.glob("reseau-*/resultats.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        for nom, v in d["services"].items():
            services[nom] = v
            dates[nom] = f.parent.name.replace("reseau-", "")
    return services, dates


def bilan(v: dict) -> dict:
    regles = {}
    for r in v["site"]:
        regles[r["rule_number"]] = r["status"]
    for p in v["pages"]:
        for c in p["controles"]:
            st = c["status"]
            prec = regles.get(c["rule_number"])
            if prec == "non-conforme" or st == "non-testé":
                regles.setdefault(c["rule_number"], st)
                continue
            if st == "non-conforme" or prec in (None, "non-testé", "non-applicable"):
                regles[c["rule_number"]] = st
    nc = sorted(n for n, s in regles.items() if s == "non-conforme")
    return {"conformes": sum(1 for s in regles.values() if s == "conforme"), "nc": nc,
            "non_testees": [p["gabarit"] for p in v["pages"] if p["statut_http"] != 200]}


def git_log() -> list[tuple[str, str, str]]:
    import subprocess
    out = subprocess.run(["git", "-C", str(RACINE), "log", "--reverse", "--format=%h|%ad|%s", "--date=format:%d/%m %H:%M"],
                         capture_output=True, text=True).stdout
    return [tuple(l.split("|", 2)) for l in out.splitlines() if l.count("|") >= 2]


def vue_ensemble(reseau: dict, dates: dict) -> str:
    sites = [x for x in SERVICES if x["cat"] == "E-commerce"]
    mails = [x for x in SERVICES if x["cat"] == "CRM"]
    nb_afaire = sum(len(items) for _, items in A_FAIRE)
    o = ['<section class="baros" aria-label="Les deux baromètres">',
         f'<a class="baro baro-sites" href="#barometre-sites"><span class="eyebrow">Baromètre 1</span><b>Sites</b>'
         f'<span>{len(sites)} sites e-commerce · {sum(len(x["ecrans"]) for x in sites)} pages</span>'
         f'<span>Opquast 245 règles + axe-core WCAG 2.1</span><span class="go">{RESUME_SITES()} →</span></a>',
         f'<a class="baro baro-mails" href="#barometre-emails"><span class="eyebrow">Baromètre 2</span><b>E-mails</b>'
         f'<span>{len(mails)} comptes e-mail · {sum(len(x["ecrans"]) for x in mails)} écrans</span>'
         f'<span>Checklist e-mail du kit</span><span class="go">{RESUME_MAILS()} →</span></a>',
         '</section>',
         '<section class="status" aria-label="État en chiffres">',
         f'<div class="stat"><b>{len(SERVICES)}</b><span>services dans le parc</span></div>',
         f'<div class="stat"><b>{sum(len(x["ecrans"]) for x in SERVICES)}</b><span>écrans à auditer</span></div>',
         f'<div class="stat now"><b>{nb_afaire}</b><span>actions restantes</span></div></section>',
         '<section class="cols">']
    for titre, groupes, marque in (("Fait", FAIT, ("done", "✓")), ("À faire", A_FAIRE, ("todo", "→"))):
        o.append(f'<div class="panel"><h2>{titre}</h2>')
        if not groupes:
            o.append('<p class="note">Rien de consigné (liste propre à la mission : referentiel/suivi-complements.json).</p>')
        for g, items in groupes:
            o.append(f'<div class="group"><h3>{e(g)}</h3><ul class="items">')
            for t, d in items:
                o.append(f'<li><span class="mark {marque[0]}">{marque[1]}</span><p>{e(t)} <small>{e(d)}</small></p></li>')
            o.append('</ul></div>')
        o.append('</div>')
    o.append('</section>')
    o.append('<section><h2>Historique Git</h2><ol class="timeline">')
    for h, d, m in git_log():
        cls = ' class="merge"' if m.startswith("Fusion") else ""
        o.append(f'<li{cls}><span class="hash">{e(h)}</span>{e(m)} <span class="when">{e(d)}</span></li>')
    o.append('</ol></section><section><h2>Liens</h2><ul class="links">')
    for t, u, d in LIENS:
        o.append(f'<li><a href="{e(u)}">{e(t)}</a><small>{e(d)}</small></li>')
    o.append('</ul></section>')
    return "\n".join(o)

REF_SITES = """
<h3>Les référentiels utilisés, et pourquoi</h3>
<div class="tbl"><table class="compact refs"><thead><tr><th>Référentiel</th><th>Ce que c'est</th><th>Pourquoi on l'utilise</th><th>Comment on le vérifie</th></tr></thead><tbody>
<tr><td><strong>Opquast « Qualité numérique » V5</strong><br><small>245 règles</small></td>
<td>Bonnes pratiques de qualité web, collaboratives et en licence ouverte, en 14 thèmes : contenus, formulaires, e-commerce, sécurité, données personnelles… Chaque règle se vérifie par oui ou non.</td>
<td>C'est le référentiel Opquast et il couvre <strong>toute la qualité d'un site</strong>, pas seulement l'accessibilité. Ses règles e-commerce (39) collent à des boutiques en ligne. Les mêmes règles sur chaque site rendent les sites du parc comparables.</td>
<td>Trois volets : nos scripts (déterministe), le robot Opquast basics d'eServices Manager (probabiliste), dont une partie contre-examinée à la main ; le reste écarté pour l'instant (voir ci-dessous).</td></tr>
<tr><td><strong>WCAG 2.1 A et AA</strong><br><small>via axe-core</small></td>
<td>Les règles internationales d'accessibilité du W3C. « A » est le minimum, « AA » le niveau attendu par la loi. axe-core (Deque, open source) vérifie automatiquement les critères mesurables.</td>
<td><strong>C'est ce que la loi demande</strong> : l'European Accessibility Act s'applique à ces sites e-commerce depuis juin 2025 et renvoie à la norme EN 301 549, donc aux WCAG 2.1 AA. Il couvre aussi des points absents d'Opquast : nom des boutons, attributs ARIA, messages d'état.</td>
<td>Automatique, dans le navigateur (<code>scripts/axe_navigateur.js</code>) : quelques secondes par page, même résultat à chaque fois, sans coût d'IA.</td></tr>
</tbody></table></div>

<h4>Qui vérifie quoi : les 245 règles Opquast</h4>
<div class="tbl"><table class="compact"><thead><tr><th>Méthode</th><th>Règles</th><th>Outil</th><th>Coût</th></tr></thead><tbody>
<tr><td><strong>Robot Opquast basics</strong> (probabiliste)</td><td class="num">65</td><td>eServices Manager, checklist native Opquast basics ; 6 règles ne relèvent que de lui</td><td>crédits IA d'eServices Manager</td></tr>
<tr><td><strong>Manuel</strong></td><td class="num">20</td><td>règles basics non scriptables : verdict du robot contre-examiné par la personne responsable</td><td>temps</td></tr>
<tr><td><strong>Réseau</strong> (déterministe)</td><td class="num">25</td><td><code>controles_reseau.py</code> v0.2.0 (19 en place), W3C i18n Checker, REDbot</td><td>aucun</td></tr>
<tr><td><strong>Code de la page</strong> (déterministe)</td><td class="num">57</td><td><code>controles_page.js</code> via Playwright sur les écrans du parc, axe-core</td><td>aucun</td></tr>
<tr><td><strong>Écartées pour l'instant</strong></td><td class="num">137</td><td>non mesurées : jugement visuel ou parcours réel (commande, compte, formulaires)</td><td>aucun</td></tr>
</tbody></table></div>
<p class="note">Les résultats des scripts et du robot sont saisis dans eServices Manager (un audit « scripts sans IA » et un audit Opquast basics par site) et réunis règle par règle dans l'onglet <a href="#etat">État et recommandations</a> et dans l'onglet de chaque site. La méthode de chaque règle figure dans l'onglet <a href="#referentiels">Référentiels</a>.</p>

<h4>Opquast et WCAG se recoupent en partie</h4>
<div class="tbl"><table class="compact"><thead><tr><th>Sujet</th><th>Règle Opquast</th><th>Critère WCAG</th></tr></thead><tbody>
<tr><td>Alternatives des images</td><td class="num">116, 117, 118</td><td class="num">1.1.1</td></tr>
<tr><td>Langue de la page</td><td class="num">130</td><td class="num">3.1.1</td></tr>
<tr><td>Contraste du texte</td><td class="num">182</td><td class="num">1.4.3</td></tr>
<tr><td>Étiquettes des champs</td><td class="num">69</td><td class="num">1.3.1, 3.3.2</td></tr>
<tr><td>Focus visible, navigation au clavier</td><td class="num">165, 166</td><td class="num">2.4.7, 2.1.1</td></tr>
<tr><td>Nom des boutons, attributs ARIA</td><td>aucune</td><td class="num">4.1.2</td></tr>
</tbody></table></div>
<p class="note">Là où les deux se recoupent, ils se contrôlent mutuellement : s'ils disent la même chose, la mesure est plus fiable ; s'ils divergent, c'est un point à vérifier à la main.</p>

<h4>Cadres légaux suivis à travers ces règles</h4>
<ul class="plain">
<li><strong>RGPD et recommandation cookies de la CNIL</strong> : règles Opquast 16, 27, 29 (données personnelles, cookies).</li>
<li><strong>CPCE, article L34-5</strong> (prospection par e-mail) : règle 173, confirmation de l'inscription à la newsletter.</li>
<li><strong>European Accessibility Act</strong> : WCAG 2.1 AA via axe-core.</li>
</ul>

<h4>Référentiels écartés</h4>
<ul class="plain">
<li><strong>RGAA</strong> (méthode française des WCAG, 106 critères) : obligatoire seulement pour les organismes publics et les entreprises de plus de 250 M€ de chiffre d'affaires ; plusieurs jours d'expertise par site. axe-core en couvre la partie automatique.</li>
<li><strong>RGESN</strong> (écoconception, 79 critères) : hors calendrier ; les 32 règles Opquast étiquetées Écoconception en donnent un premier signal.</li>
</ul>
"""

REF_EMAILS = """
<h3>Le référentiel utilisé, et pourquoi</h3>
<div class="tbl"><table class="compact refs"><thead><tr><th>Référentiel</th><th>Ce que c'est</th><th>Pourquoi on l'utilise</th><th>Comment on le vérifie</th></tr></thead><tbody>
<tr><td><strong>Checklist e-mail du kit</strong><br><small>referentiel/checklist-email.csv</small></td>
<td>Critères propres aux e-mails et aux formulaires d'inscription, en 6 thèmes : accessibilité, contenu, conformité, délivrabilité, formulaires, mode sombre. 26 critères sont reliés à une règle Opquast.</td>
<td><strong>Opquast est fait pour le web</strong> : plus de la moitié de ses règles n'a pas de sens pour un e-mail (sitemap, robots.txt, page 404, navigation…), et il ne parle ni de texte de prévisualisation, ni de désinscription en un clic, ni d'authentification du domaine d'envoi, ni de mode sombre.</td>
<td>Script sur le HTML des templates lus par le connecteur de l'outil d'envoi (lecture seule) et DNS du domaine d'envoi, puis jugement IA (Claude) ; parcours réels à la main. Résultats importés dans eServices Manager.</td></tr>
</tbody></table></div>

<h4>D'où viennent les critères</h4>
<div class="tbl"><table class="compact"><thead><tr><th>Source</th><th>Critères</th><th>Pourquoi cette source</th></tr></thead><tbody>
<tr><td><strong>W3C, WCAG 2.1 et 2.2</strong></td><td>Accessibilité (EM01 à EM12)</td><td>Un e-mail est du HTML : les mêmes règles d'accessibilité s'appliquent (alternatives, contraste, langue, intitulés de liens).</td></tr>
<tr><td><strong>Aide Klaviyo</strong> (e-mails et formulaires accessibles, délivrabilité)</td><td>Contenu, formulaires, délivrabilité</td><td>Un outil d'envoi répandu : ses recommandations et ses réglages (contour de focus, alertes de l'éditeur, domaine d'envoi).</td></tr>
<tr><td><strong>CNIL et CPCE article L34-5</strong></td><td>Conformité (EM18 à EM24)</td><td>La loi française de la prospection par e-mail : consentement préalable, désinscription simple, identité de l'annonceur.</td></tr>
<tr><td><strong>Exigences de Gmail et Yahoo</strong> (2024)</td><td>Délivrabilité (EM25 à EM29)</td><td>Sans SPF, DKIM, DMARC et désinscription en un clic, les e-mails n'arrivent plus en boîte de réception chez ces fournisseurs.</td></tr>
<tr><td><strong>Can I Email</strong> (open source, licence MIT) et guides Litmus</td><td>Mode sombre (EM35 à EM41)</td><td>Tableaux de compatibilité client par client : Gmail et Yahoo ignorent les styles prévus pour le mode sombre, Outlook Windows inverse tout, Apple Mail les respecte.</td></tr>
</tbody></table></div>
<p class="note">Les seuils de taux de plaintes (0,3 % et 0,1 %) viennent de synthèses tierces et du blog Klaviyo : à revérifier dans la documentation de Google avant de les présenter comme des obligations. Liste complète : onglet <a href="#referentiels">Référentiels</a>.</p>
"""


def graphiques_parc(sites: list) -> str:
    noms = [x["nom"] for x in sites]
    SCS = {n: scores_site(n) for n in noms}
    ec = []
    for n in noms:
        rec = LECTURE.get(n, {}).get("recoupement", {})
        ec.append((n, sum(1 for v in rec.values() if {x for x in v.values() if x in ("C", "NC")} == {"C", "NC"}), ""))
    ec = [(n, v, f"{v} règle(s)") for n, v, _ in ec]
    return ('<div class="viz-grille">'
            + svg_barres([(n, SCS[n]["global"], f'{SCS[n]["global"]} %, note {note_lettre(SCS[n]["global"])}') for n in noms if SCS[n]["global"] is not None], 100, "Score du baromètre : conformité Opquast par site")
            + svg_empile([(n, comptes_statuts(ETAT.get("sites", {}).get(n, {}))) for n in noms], "Règles Opquast par statut")
            + svg_barres(ec, max([v for _, v, _ in ec] or [1]), "Règles où les outils se contredisent (à trancher par la lecture critique)")
            + '</div>')


def onglet_barometre_sites(reseau: dict, dates: dict) -> str:
    sites = [x for x in SERVICES if x["cat"] == "E-commerce"]
    o = ['<section class="tab" id="barometre-sites" role="tabpanel" aria-labelledby="t-barometre-sites" hidden>',
         '<div class="svc-head"><div class="eyebrow">Baromètre 1</div><h2>Baromètre des sites</h2>',
         f'<p class="lede">Un seul objectif de contrôle : la conformité des {len(sites)} sites du parc aux règles Opquast V5. '
         'Trois audits Opquast tranchent les règles ; les autres outils servent seulement à recouper ces règles. Une ligne par audit ou outil, une colonne par site.</p></div>',
         graphiques_parc(sites),
         '<h3>Ce qui compose le baromètre, site par site</h3>',
         '<div class="tbl"><table class="compact baro-table"><thead><tr><th>Ce qui compose le baromètre</th>'
         + "".join(f'<th><a href="#{x["id"]}">{e(x["nom"])}</a></th>' for x in sites) + '</tr></thead><tbody>']
    SCS = {x["nom"]: scores_site(x["nom"]) for x in sites}
    o.append('<tr class="synthese"><td><strong>Score du baromètre</strong><br><small>taux de conformité Opquast, toutes sources</small></td>'
             + "".join(f'<td>{pastille_score(SCS[x["nom"]]["global"])}</td>' for x in sites) + '</tr>')
    for k, lib, poids, _ in FAMILLES:
        o.append(f'<tr class="synthese"><td>{e(lib)} <small>({poids} %)</small></td>' + "".join(f'<td>{pastille_score(SCS[x["nom"]]["familles"][k], True)}</td>' for x in sites) + '</tr>')
    # ligne de synthèse
    o.append('<tr class="synthese"><td><strong>Conformité Opquast</strong><br><small>règles conformes sur règles tranchées, toutes sources</small></td>')
    for x in sites:
        st = [v["statut"] for v in ETAT.get("sites", {}).get(x["nom"], {}).values()]
        c, nc = st.count("C"), st.count("NC")
        o.append(f'<td><strong>{100 * c / (c + nc):.0f} %</strong><br><small>{c} C, {nc} NC</small></td>' if c + nc else '<td>-</td>')
    o.append('</tr>')
    for k, n, typ, quoi, f in COMPOSANTS:
        o.append(f'<tr><td><strong>{e(n)}</strong> {pastille("info", typ)}<br><small>{e(quoi)}</small></td>')
        for x in sites:
            res, cls, url = f(x["nom"], ETAT.get("sites", {}).get(x["nom"], {}))
            txt = f'<a href="{e(url)}" target="_blank" rel="noopener">{e(res)}</a>' if url else e(res)
            scr = SCS[x["nom"]].get(k)
            o.append(f'<td class="c-{cls}">' + (pastille_score(scr, True) + '<br>' if k in AUDITS_SCORES else '') + f'{txt}<br><small><a href="#{x["id"]}">détail</a></small></td>')
        o.append('</tr>')
    o.append('</tbody></table></div>'
             '<p class="note">Un résultat souligné ouvre l\'audit (eServices Manager ou service en ligne). « détail » ouvre l\'onglet du site, où chaque mesure a son accordéon.</p>'
             + bloc_methode_scores() + '</section>')
    return "\n".join(o)


def onglet_barometre_emails() -> str:
    import csv
    mails = [x for x in SERVICES if x["cat"] == "CRM"]
    crit = list(csv.DictReader((RACINE / "referentiel" / "checklist-email.csv").open(encoding="utf-8")))
    themes = {}
    for c in crit:
        themes.setdefault(c["theme"], []).append(c["id"])
    o = ['<section class="tab" id="barometre-emails" role="tabpanel" aria-labelledby="t-barometre-emails" hidden>',
         '<div class="svc-head"><div class="eyebrow">Baromètre 2</div><h2>Baromètre des e-mails</h2>',
         f'<p class="lede">{len(mails)} compte(s) e-mail, {len(SUFFIXES_EMAIL)} écrans types chacun (popup, pied de page, bienvenue, panier abandonné, post-achat, campagne). '
         f'Référentiel : checklist e-mail du kit, {len(crit)} critères. Comptes en lecture seule.</p></div>',
         REF_EMAILS,
         '<h3>Où en est chaque compte</h3><div class="tbl"><table><thead><tr><th>Compte</th><th>Accès</th>'
         '<th>Critères évalués</th><th>Mode sombre</th><th>Écrans</th></tr></thead><tbody>']
    for x in mails:
        lu = x["nom"] in ETAT.get("emails", {})
        o.append(f'<tr><td><a href="#{x["id"]}"><strong>{e(x["nom"])}</strong></a></td>'
                 f'<td>{pastille("ok" if lu else "ko", "lecture OK" if lu else "à ouvrir")}</td>'
                 f'<td>{CRIT_COMPTE(x["nom"], len(crit))}</td><td>{SOMBRE_COMPTE(x["nom"])}</td>'
                 f'<td class="num">{len(x["ecrans"])}</td></tr>')
    o.append('</tbody></table></div>')
    o.append('<h3>Les critères, par thème</h3><div class="tbl"><table class="compact"><thead><tr><th>Thème</th><th>Critères</th>'
             + "".join(f'<th>{e(x["nom"])}</th>' for x in mails) + '</tr></thead><tbody>')
    for th, ids in themes.items():
        o.append(f'<tr><td><strong>{e(th)}</strong></td><td class="num">{len(ids)} ({ids[0]} à {ids[-1]})</td>'
                 + "".join(f'<td>{THEME_COMPTE(x["nom"], th) if x["nom"] in ETAT.get("emails", {}) else pastille("info", "accès à ouvrir")}</td>' for x in mails) + '</tr>')
    o.append('</tbody></table></div>')
    o.append('<h3>Reste à faire sur ce baromètre</h3><ul class="items">')
    a_connecter = [x["nom"] for x in mails if x["nom"] not in ETAT.get("emails", {})]
    for t in [f"Connecter le compte {n} et choisir ses écrans" for n in a_connecter] + [
              "Relire les jugements IA sur les e-mails (consentement, contraste) et finaliser les audits",
              "Tester à la main les critères de parcours (clavier, lecteur d'écran, désinscription)",
              "Captures en mode sombre dans Gmail, Outlook Windows et Apple Mail"]:
        o.append(f'<li><span class="mark todo">→</span><p>{e(t)}</p></li>')
    o.append('</ul><p class="note">Liste complète des critères et de leurs sources : onglet <a href="#referentiels">Référentiels</a>.</p></section>')
    return "\n".join(o)


def remplir_tests(s: dict, reseau: dict, axe: dict | None = None, dates: dict | None = None) -> None:
    tests = []
    for t in s["tests"]:
        if t[3] == "RESEAU":
            if s["reseau"] in reseau:
                b = bilan(reseau[s["reseau"]])
                txt = f'{b["conformes"]} conformes, {len(b["nc"])} non conformes ({", ".join(map(str, b["nc"])) or "aucune"})'
                if b["non_testees"]:
                    txt += f' ; non testé : {", ".join(b["non_testees"])}'
                tests.append((t[0] or (dates or {}).get(s["reseau"], ""), t[1], t[2], "attention" if b["nc"] else "ok", txt))
            else:
                tests.append((t[0], t[1], t[2], "afaire", "Passage en cours"))
        else:
            tests.append(t)
    if axe and s["nom"] in axe.get("sites", {}):
        a = axe["sites"][s["nom"]]
        tests.append((axe.get("date", ""), f'Accessibilité automatique, WCAG 2.1 A et AA ({a["pages_testees"]} pages)', "axe-core 4.10.2, navigateur",
                      "attention" if a["regles_en_violation"] else "ok",
                      f'{a["regles_en_violation"]} règles en violation, dont {a["regles_critiques"]} critiques ; {a["elements_en_defaut"]} éléments en défaut'))
    s["tests"] = tests


def main() -> None:
    page = PAGE.read_text(encoding="utf-8")
    reseau, dates = charger_reseau()
    axe = charger_axe()
    AXE.update(axe)
    ETAT.update(charger_etat())
    COMPLEMENTS.clear()
    COMPLEMENTS.update(charger_complements())
    FAIT[:], A_FAIRE[:] = COMPLEMENTS.get("fait", []), COMPLEMENTS.get("a_faire", [])
    LIENS[:] = [tuple(x) for x in COMPLEMENTS.get("liens", [])] + liens_locaux()
    SERVICES[:] = construire_services()
    charger_annexes()
    exporter_scores([x["nom"] for x in SERVICES if x["cat"] == "E-commerce"])
    for s in SERVICES:
        remplir_tests(s, reseau, axe, dates)
    tete = page[:page.index('<div class="wrap">')]
    tete = re.sub(r"/\* Onglets \*/.*?(?=@media \(prefers-reduced-motion)", "", tete, flags=re.S)
    tete = tete.replace("@media (prefers-reduced-motion", CSS_ONGLETS.lstrip("\n") + "@media (prefers-reduced-motion", 1)
    aujourdhui = max(dates.values()) if dates else ""
    j = COMPLEMENTS.get("jalons", [])
    li = lambda c, t: f'      <li class="{c}">{e(t)}</li>\n' if c else f'      <li>{e(t)}</li>\n'
    jalons = ('    <ul class="milestones" aria-label="Jalons">\n' + "".join(li(c, t) for c, t in j) + '    </ul>\n') if j else ""
    entete = f"""<div class="wrap">
  <header>
    <div class="eyebrow">Baromètre qualité Opquast · {e(qui())}</div>
    <h1>Suivi des baromètres Opquast</h1>
    <p class="lede">Deux baromètres qualité du parc, un pour les sites et un pour les e-mails : ce qui a été fait, testé et vérifié, et ce qui reste à faire. Un onglet par service. Dernier contrôle réseau : {e(aujourdhui)}.</p>
{jalons}  </header>
"""
    sites = [x for x in SERVICES if x["cat"] == "E-commerce"]
    mails = [x for x in SERVICES if x["cat"] == "CRM"]
    nav = ['<nav class="tabs-nav" aria-label="Navigation du suivi">',
           '<ul class="tabs tabs-main" role="tablist">',
           '<li><a id="t-ensemble" role="tab" href="#ensemble">Vue d\'ensemble</a></li>',
           f'<li><a id="t-barometre-sites" role="tab" href="#barometre-sites" class="t-sites">Baromètre des sites<small>{len(sites)}</small></a></li>',
           f'<li><a id="t-barometre-emails" role="tab" href="#barometre-emails" class="t-mails">Baromètre des e-mails<small>{len(mails)}</small></a></li>',
           '<li><a id="t-etat" role="tab" href="#etat">État et recommandations</a></li>',
           '<li><a id="t-referentiels" role="tab" href="#referentiels">Référentiels<small>245 + 41</small></a></li></ul>',
           '<div class="tabs-sub"><span class="sub-label">Sites</span><ul class="tabs">']
    nav += [f'<li><a id="t-{x["id"]}" role="tab" href="#{x["id"]}">{e(x["nom"])}<small>{TAUX_NAV(x["nom"])}</small></a></li>' for x in sites]
    nav.append('</ul></div><div class="tabs-sub"><span class="sub-label">E-mails</span><ul class="tabs">')
    nav += [f'<li><a id="t-{x["id"]}" role="tab" href="#{x["id"]}">{e(x["nom"])}<small>{TAUX_NAV(x["nom"])}</small></a></li>' for x in mails]
    nav.append('</ul></div></nav>')
    corps = (entete + "\n".join(nav) + '\n<section class="tab" id="ensemble" role="tabpanel" aria-labelledby="t-ensemble">'
             + vue_ensemble(reseau, dates) + '</section>\n' + onglet_barometre_sites(reseau, dates) + "\n" + onglet_barometre_emails() + "\n" + "\n".join(onglet(s, reseau) for s in SERVICES) + "\n" + onglet_etat() + "\n" + onglet_referentiels()
             + '\n  <footer>Sources : dépôt Git du projet, referentiel/parc.json, tests d\'accès, contrôles réseau (resultats/), test du MCP Opquast. '
               + (e(COMPLEMENTS["pied"]) + ' ' if COMPLEMENTS.get("pied") else '') + 'Page générée par scripts/generer_suivi.py.</footer>\n</div>\n')
    PAGE.write_text((tete + corps + JS_ONGLETS).replace(" — ", " - ").replace("—", "-"), encoding="utf-8")  # aucun tiret long dans le livrable, même cité
    print(f"{PAGE.name} : {len(SERVICES)} onglets de service")


if __name__ == "__main__":
    main()
