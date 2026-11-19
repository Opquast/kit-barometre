// Tests de scripts/outils_j2.mjs : Pa11y, Blacklight, xmllint (execFileSync), fetch et Playwright remplacés par des faux.
import { test, mock } from 'node:test';
import assert from 'node:assert/strict';
import { writeFileSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { enfant, lancer, preparerEnfant, urlScript, DATE } from './aide_outils.mjs';

const CHROME = '/faux/chromium';
const XML_INDEX = '<?xml version="1.0"?><sitemapindex><sitemap><loc>https://s.fr/a.xml</loc></sitemap><sitemap><loc>https://s.fr/b.xml</loc></sitemap></sitemapindex>';
// Réponses de fetch : plan du site et PageSpeed Insights, par origine.
const SITEMAP = {
  'https://s.fr': { status: 200, xml: XML_INDEX },
  'https://t.fr': { status: 404, xml: '<urlset><url>' },
  'https://u.fr': { lance: 'fetch failed' },
};
const PSI = {
  'https://s.fr/': { loadingExperience: { overall_category: 'AVERAGE', metrics: {
    LARGEST_CONTENTFUL_PAINT_MS: { percentile: 2600, category: 'AVERAGE' }, INTERACTION_TO_NEXT_PAINT: { percentile: 150, category: 'FAST' } } },
  lighthouseResult: { categories: { performance: { score: 0.424 } } } },
  'https://t.fr/': { error: { message: 'Quota dépassé' } },
};
const BLACKLIGHT = {
  'https://s.fr/': { reports: { cookies: [{ third_party: true }, { third_party: false }, { third_party: true }],
    third_party_trackers: { 'doubleclick.net': 1, 'criteo.com': 2 }, fb_pixel_events: [{}], google_analytics_events: [],
    session_recorders: { hotjar: [] }, canvas_fingerprinters: { fingerprinters: ['https://fp.js'] } } },
  'https://t.fr/': {},
  'https://u.fr/': { lance: 'Chrome a planté\npile' },
  'https://v.fr/': { reports: { third_party_trackers: 7, fb_pixel_events: null, canvas_fingerprinters: {} } },
  'https://w.fr/': { reports: { canvas_fingerprinters: { fingerprinters: [] }, google_analytics_events: { G1: 1 } } },
};
const PA11Y = {
  'https://s.fr/': { issues: [
    { type: 'error', code: 'WCAG2AA.Principle1.Guideline1_1.1_1_1.H37' },
    { type: 'error', code: 'WCAG2AA.Principle1.Guideline1_1.1_1_1.H37' },
    { type: 'error', code: 'WCAG2AA.Principle4.Guideline4_1.4_1_2.H91.A.NoContent' },
    { type: 'warning', code: 'w' }, { type: 'notice', code: 'n' }] },
  'https://s.fr/account': { final: 'https://shopify.com/account', issues: [] },
  'https://s.fr/panne': { lance: 'TimeoutError: délai\npile' },
};
const CSV = `service,gabarit,url
S,Accueil,https://s.fr/
S,Compte,https://s.fr/account
S,Panne,https://s.fr/panne
T,Produit,https://t.fr/p
T,Accueil,https://t.fr/
U,Accueil,https://u.fr/
V,Accueil,https://v.fr/
W,Accueil,https://w.fr/
`;

if (enfant) {
  const { tmp, rediriger } = preparerEnfant(mock, 'outils_j2.mjs');
  const journal = { fetch: [], xmllint: [], blacklight: [], pa11y: [] };
  mock.module('playwright', { namedExports: { chromium: { executablePath: () => CHROME } } });
  globalThis.fetch = async (url, opts) => {
    journal.fetch.push([url, opts]);
    const u = new URL(url);
    if (u.pathname === '/sitemap.xml') {
      const c = SITEMAP[u.origin];
      if (c.lance) throw new Error(c.lance);
      return { status: c.status, text: async () => c.xml };
    }
    const cible = u.searchParams.get('url');
    return { json: async () => PSI[cible] ?? {} };
  };
  mock.module('node:child_process', { namedExports: { execFileSync: (cmd, a, opts) => {
    const xml = readFileSync(rediriger(a[1]), 'utf8');
    journal.xmllint.push({ cmd, a0: a[0], xml, opts });
    if (xml.includes('<urlset>')) { const e = new Error('xmllint'); e.stderr = Buffer.from(`${a[1]}:1: parser error : Premature end of data\n<urlset><url>`); throw e; }
    return Buffer.from('');
  } } });
  mock.module('pa11y', { defaultExport: async (url, opts) => {
    journal.pa11y.push([url, opts]);
    const c = PA11Y[url] ?? { issues: [{ type: 'error', code: 'a.b.c' }] };
    if (c.lance) throw new Error(c.lance);
    return { issues: c.issues, pageUrl: c.final ?? url };
  } });
  const interaction = { fillForms: 'remplissage original' };
  mock.module('@themarkup/blacklight-collector/build/pptr-utils/interaction-utils.js', { defaultExport: interaction });
  mock.module('@themarkup/blacklight-collector', { defaultExport: { collect: async (url, opts) => {
    journal.blacklight.push([url, opts]);
    const c = BLACKLIGHT[url];
    if (c.lance) throw new Error(c.lance);
    return c;
  } } });
  process.on('exit', () => writeFileSync(join(tmp, 'journal.json'), JSON.stringify(journal)));
  await import(urlScript('outils_j2.mjs'));
  // le remplissage des formulaires de Blacklight est remplacé par une fonction qui ne fait rien
  journal.fillForms = { type: typeof interaction.fillForms, resultat: String(await interaction.fillForms()) };
} else {
  const dossier = `resultats/outils-${DATE}`;

  test('tous les outils sur tous les services, avec leurs erreurs', t => {
    const r = lancer(import.meta.url, 'tous', { csv: CSV });
    t.after(r.nettoyer);
    assert.equal(r.statut, 0, r.erreurs);
    const res = r.json(`${dossier}/j2.json`);
    assert.deepEqual(Object.keys(res), ['S', 'T', 'U', 'V', 'W']);

    assert.deepEqual(res.S.sitemap, { url: 'https://s.fr/sitemap.xml', statut_http: 200, bien_forme: true, erreur: '', index: true, entrees: 2 });
    assert.equal(res.T.sitemap.bien_forme, false);
    assert.equal(res.T.sitemap.statut_http, 404);
    assert.match(res.T.sitemap.erreur, /parser error : Premature end of data$/);
    assert.equal(res.T.sitemap.index, false);
    assert.equal(res.T.sitemap.entrees, 0);
    assert.deepEqual(res.U.sitemap, { erreur: 'fetch failed' });
    assert.ok(!r.existe(`${dossier}/.sitemap.xml`), 'fichier temporaire du plan supprimé');

    assert.deepEqual(res.S.psi, { url: 'https://s.fr/', donnees_terrain: 'AVERAGE',
      lcp_ms: { p75: 2600, categorie: 'AVERAGE' }, inp_ms: { p75: 150, categorie: 'FAST' }, cls_x100: null,
      perf_labo_mobile: 42, details_url: 'https://pagespeed.web.dev/analysis?url=https%3A%2F%2Fs.fr%2F' });
    assert.deepEqual(res.T.psi, { erreur: 'Quota dépassé' });
    assert.equal(res.U.psi.donnees_terrain, 'aucune (trafic insuffisant pour CrUX)');
    assert.equal(res.U.psi.lcp_ms, null);
    assert.equal(res.U.psi.perf_labo_mobile, 0);

    assert.deepEqual(res.S.blacklight, { cookies_tiers: 2, cookies: 3, traceurs_tiers: 2, pixel_facebook: true, google_analytics: false,
      enregistreurs_de_session: ['hotjar'], empreinte_canvas: true });
    assert.deepEqual(res.T.blacklight, { cookies_tiers: 0, cookies: 0, traceurs_tiers: 0, pixel_facebook: false, google_analytics: false,
      enregistreurs_de_session: [], empreinte_canvas: false });
    assert.deepEqual(res.U.blacklight, { erreur: 'Chrome a planté' });
    assert.equal(res.V.blacklight.traceurs_tiers, 0);
    assert.equal(res.V.blacklight.empreinte_canvas, false);
    assert.equal(res.W.blacklight.empreinte_canvas, false);
    assert.equal(res.W.blacklight.google_analytics, true);

    assert.deepEqual(res.S.pages['https://s.fr/'], { gabarit: 'Accueil', pa11y: { erreurs: 3, avertissements: 1,
      par_code: { '1_1_1.H37': 2, 'A.NoContent': 1 }, url_finale: 'https://s.fr/' } });
    assert.deepEqual(res.S.pages['https://s.fr/account'].pa11y, { non_teste: 'quitte le site (compte client hébergé par Shopify)' });
    assert.deepEqual(res.S.pages['https://s.fr/panne'].pa11y, { non_teste: 'TimeoutError: délai' });
    assert.deepEqual(Object.keys(res.T.pages), ['https://t.fr/p', 'https://t.fr/']);

    const j = r.json('journal.json');
    assert.deepEqual(j.fillForms, { type: 'function', resultat: 'undefined' });
    assert.deepEqual(j.xmllint[0].a0, '--noout');
    assert.equal(j.xmllint[0].xml, XML_INDEX);
    assert.equal(j.xmllint.length, 2);
    assert.equal(j.fetch[0][1].headers['User-Agent'], 'Opquast-barometre-Colorz/0.3 (lecture seule)');
    assert.ok(j.fetch.some(([u]) => u === 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https%3A%2F%2Ft.fr%2F&strategy=mobile&category=performance'));
    // Blacklight sur l'accueil uniquement, sans test de captation de frappe, avec le Chromium de Playwright
    assert.deepEqual(j.blacklight.map(b => b[0]), ['https://s.fr/', 'https://t.fr/', 'https://u.fr/', 'https://v.fr/', 'https://w.fr/']);
    assert.equal(j.blacklight[0][1].puppeteerExecutablePath, CHROME);
    assert.ok(!j.blacklight[0][1].blTests.includes('key_logging'));
    assert.equal(j.pa11y.length, 8);
    assert.deepEqual(j.pa11y[0][1].chromeLaunchConfig, { executablePath: CHROME, args: ['--no-sandbox'] });
    assert.equal(j.pa11y[0][1].standard, 'WCAG2AA');
    assert.match(r.sortie, /S \| Accueil \| pa11y 3 erreurs/);
    assert.match(r.sortie, /S \| Panne \| pa11y TimeoutError: délai/);
  });

  test('--service et --sans pa11y : les résultats déjà présents ne sont pas refaits', t => {
    const deja = { S: { pages: {}, sitemap: { ancien: 1 }, psi: { ancien: 2 }, blacklight: { ancien: 3 } } };
    const r = lancer(import.meta.url, 'reprise', { csv: CSV, argv: ['--service', 'S', '--sans', 'pa11y'],
      fichiers: { [`${dossier}/j2.json`]: deja } });
    t.after(r.nettoyer);
    assert.equal(r.statut, 0, r.erreurs);
    assert.deepEqual(r.json(`${dossier}/j2.json`), deja);
    const j = r.json('journal.json');
    assert.equal(j.fetch.length + j.blacklight.length + j.pa11y.length, 0);
  });

  test('--sans sitemap,psi,blacklight : seul Pa11y tourne, sur les pages qui ne l\'ont pas', t => {
    const r = lancer(import.meta.url, 'pa11y', { csv: CSV, argv: ['--sans', 'sitemap,psi,blacklight'],
      fichiers: { [`${dossier}/j2.json`]: { S: { pages: {
        'https://s.fr/': { gabarit: 'Accueil', pa11y: { erreurs: 9 } },
        'https://s.fr/account': { gabarit: 'Compte', autre: true } } } } } });
    t.after(r.nettoyer);
    assert.equal(r.statut, 0, r.erreurs);
    const res = r.json(`${dossier}/j2.json`);
    assert.deepEqual(res.S.pages['https://s.fr/'].pa11y, { erreurs: 9 });
    assert.equal(res.S.pages['https://s.fr/account'].autre, true);
    assert.ok(res.S.pages['https://s.fr/account'].pa11y.non_teste);
    assert.equal(res.S.sitemap, undefined);
    assert.equal(res.V.pages['https://v.fr/'].pa11y.par_code['b.c'], 1);
    const j = r.json('journal.json');
    assert.equal(j.fetch.length + j.blacklight.length, 0);
    assert.equal(j.pa11y.length, 7);
  });
}
