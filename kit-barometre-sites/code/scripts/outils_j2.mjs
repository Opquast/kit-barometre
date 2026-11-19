// Outils complémentaires du support J2, lancés en plus des autres pour recouper les résultats (faux positifs et
// faux négatifs), lecture seule :
// - Pa11y 10 avec le moteur HTML_CodeSniffer (LGPL) : accessibilité WCAG 2 AA, moteur différent d'axe-core et d'IBM ;
// - PageSpeed Insights (API Google, sans clé) : données réelles des visiteurs Chrome (CrUX) quand elles existent,
//   en plus des mesures de laboratoire de Lighthouse ;
// - Blacklight collector (The Markup) : traceurs tiers, cookies, pixel Facebook, Google Analytics, enregistreurs de
//   session, empreinte canvas, sur l'accueil, sans consentement (sans son test de captation de frappe, qui remplit les champs) ;
// - Sitemap : récupération de /sitemap.xml et contrôle de bonne forme avec xmllint (règle Opquast 220).
//
// Usage : node scripts/outils_j2.mjs [--service "Boutique A"] [--sans pa11y,psi,blacklight,sitemap]
// Sortie : resultats/outils-AAAA-MM-JJ/j2.json (incrémental)
import { chromium } from 'playwright';
import { readFileSync, writeFileSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import pa11y from 'pa11y';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
// Blacklight remplit les champs des pages avec des valeurs fictives pour son test de captation de frappe (sans envoi).
// On ne saisit rien sur les sites des clients : remplissage désactivé, test de captation de frappe retiré.
require('@themarkup/blacklight-collector/build/pptr-utils/interaction-utils.js').fillForms = async () => {};
const { collect } = require('@themarkup/blacklight-collector');

const RACINE = new URL('..', import.meta.url).pathname;
const args = process.argv.slice(2);
const seul = args.includes('--service') ? args[args.indexOf('--service') + 1] : null;
const sans = new Set((args.includes('--sans') ? args[args.indexOf('--sans') + 1] : '').split(','));
const CHROME = chromium.executablePath();
const pause = ms => new Promise(ok => setTimeout(ok, ms));
const lignes = readFileSync(`${RACINE}scripts/ecrans_en_ligne.csv`, 'utf8').trim().split('\n').slice(1).map(l => {
  const [service, gabarit, ...u] = l.split(','); return { service, gabarit, url: u.join(',') };
}).filter(e => !seul || e.service === seul);
const date = new Date().toISOString().slice(0, 10);
const dossier = `${RACINE}resultats/outils-${date}`;
mkdirSync(dossier, { recursive: true });
const fichier = `${dossier}/j2.json`;
const res = existsSync(fichier) ? JSON.parse(readFileSync(fichier, 'utf8')) : {};
const sauver = () => writeFileSync(fichier, JSON.stringify(res, null, 1));

for (const nom of [...new Set(lignes.map(e => e.service))]) {
  const s = (res[nom] ??= { pages: {} });
  const accueil = lignes.find(e => e.service === nom && e.gabarit.startsWith('Accueil')).url;
  const hote = new URL(accueil).origin;

  if (!sans.has('sitemap') && !s.sitemap) {
    try {
      const rep = await fetch(`${hote}/sitemap.xml`, { headers: { 'User-Agent': 'Opquast-barometre-Colorz/0.3 (lecture seule)' } });
      const xml = await rep.text();
      const tmp = `${dossier}/.sitemap.xml`; writeFileSync(tmp, xml);
      let bien_forme = true, erreur = '';
      try { execFileSync('xmllint', ['--noout', tmp], { stdio: 'pipe' }); } catch (e) { bien_forme = false; erreur = String(e.stderr).split('\n')[0].slice(0, 160); }
      rmSync(tmp);
      s.sitemap = { url: `${hote}/sitemap.xml`, statut_http: rep.status, bien_forme, erreur, index: /<sitemapindex/.test(xml),
        entrees: (xml.match(/<loc>/g) || []).length };
    } catch (e) { s.sitemap = { erreur: String(e.message).slice(0, 120) }; }
    console.log(nom, 'sitemap', JSON.stringify(s.sitemap)); sauver();
  }

  if (!sans.has('psi') && !s.psi) {
    try {
      const u = `https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=${encodeURIComponent(accueil)}&strategy=mobile&category=performance`;
      const d = await (await fetch(u)).json();
      if (d.error) throw new Error(d.error.message);
      const terrain = d.loadingExperience?.metrics || {};
      const m = k => terrain[k] ? { p75: terrain[k].percentile, categorie: terrain[k].category } : null;
      s.psi = { url: accueil, donnees_terrain: d.loadingExperience?.overall_category || 'aucune (trafic insuffisant pour CrUX)',
        lcp_ms: m('LARGEST_CONTENTFUL_PAINT_MS'), inp_ms: m('INTERACTION_TO_NEXT_PAINT'), cls_x100: m('CUMULATIVE_LAYOUT_SHIFT_SCORE'),
        perf_labo_mobile: Math.round((d.lighthouseResult?.categories?.performance?.score || 0) * 100),
        details_url: `https://pagespeed.web.dev/analysis?url=${encodeURIComponent(accueil)}` };
    } catch (e) { s.psi = { erreur: String(e.message).slice(0, 160) }; }
    console.log(nom, 'psi', JSON.stringify(s.psi).slice(0, 200)); sauver(); await pause(5000);
  }

  if (!sans.has('blacklight') && !s.blacklight) {
    try {
      const r = await collect(accueil, { numPages: 1, headless: true, captureHar: false, saveScreenshots: false, puppeteerExecutablePath: CHROME,
        blTests: ['cookies', 'fb_pixel_events', 'google_analytics_events', 'session_recorders', 'third_party_trackers', 'canvas_fingerprinters'] });
      const rep = r.reports || {};
      const n = x => Array.isArray(x) ? x.length : x && typeof x === 'object' ? Object.keys(x).length : 0;
      s.blacklight = { cookies_tiers: (rep.cookies || []).filter(c => c.third_party).length, cookies: n(rep.cookies),
        traceurs_tiers: n(rep.third_party_trackers), pixel_facebook: n(rep.fb_pixel_events) > 0, google_analytics: n(rep.google_analytics_events) > 0,
        enregistreurs_de_session: Object.keys(rep.session_recorders || {}),         empreinte_canvas: !!(rep.canvas_fingerprinters && rep.canvas_fingerprinters.fingerprinters && rep.canvas_fingerprinters.fingerprinters.length) };
    } catch (e) { s.blacklight = { erreur: String(e.message).split('\n')[0].slice(0, 160) }; }
    console.log(nom, 'blacklight', JSON.stringify(s.blacklight).slice(0, 220)); sauver(); await pause(5000);
  }

  if (!sans.has('pa11y')) {
    for (const e of lignes.filter(x => x.service === nom)) {
      if (s.pages[e.url]?.pa11y) continue;
      const p = (s.pages[e.url] ??= { gabarit: e.gabarit });
      try {
        const r = await pa11y(e.url, { standard: 'WCAG2AA', runners: ['htmlcs'], timeout: 60000, wait: 3000,
          chromeLaunchConfig: { executablePath: CHROME, args: ['--no-sandbox'] } });
        const err = r.issues.filter(i => i.type === 'error');
        const parCode = {};
        for (const i of err) { const k = i.code.split('.').slice(-2).join('.'); parCode[k] = (parCode[k] || 0) + 1; }
        p.pa11y = { erreurs: err.length, avertissements: r.issues.filter(i => i.type === 'warning').length, par_code: parCode,
          url_finale: r.pageUrl };
        if (new URL(r.pageUrl).host !== new URL(e.url).host) p.pa11y = { non_teste: 'quitte le site (compte client hébergé par Shopify)' };
      } catch (err) { p.pa11y = { non_teste: String(err.message).split('\n')[0].slice(0, 120) }; }
      console.log(nom, '|', e.gabarit, '| pa11y', p.pa11y.non_teste || `${p.pa11y.erreurs} erreurs`); sauver(); await pause(5000);
    }
  }
}
console.log(fichier);
