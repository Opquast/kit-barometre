// Tests de scripts/outils_page.mjs : Playwright (Chromium, CDP), IBM Equal Access, Lighthouse et chrome-launcher
// remplacés par des faux. Aucun site réel, aucun navigateur lancé.
import { test, mock } from 'node:test';
import assert from 'node:assert/strict';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { enfant, lancer, preparerEnfant, urlScript, fauxDocument, DATE, RACINE_SCRIPT } from './aide_outils.mjs';

// Quantiles de l'EcoIndex : une page « au quantile x » sur les trois critères a un score de 100 - 5x.
const Q_DOM = [0, 47, 75, 159, 233, 298, 358, 417, 476, 537, 603, 674, 753, 843, 949, 1076, 1237, 1459, 1801, 2479, 594601];
const Q_REQ = [0, 2, 15, 25, 34, 42, 49, 56, 63, 70, 78, 86, 95, 105, 117, 130, 147, 170, 205, 281, 3920];
const Q_SIZE = [0, 1.37, 144.7, 319.53, 479.46, 631.97, 783.38, 937.91, 1098.62, 1265.47, 1448.32, 1648.27, 1876.08, 2142.06, 2465.37, 2866.31, 3401.59, 4155.73, 5400.08, 8037.54, 223212.26];
const auQuantile = x => ({ dom: Q_DOM[x], req: Q_REQ[x], octets: Math.ceil(Q_SIZE[x] * 1024) + (x === 20 ? 4096 : 1) });

const AUDITS = ['meta-description', 'image-alt', 'link-name', 'color-contrast', 'viewport', 'is-on-https', 'uses-text-compression',
  'uses-long-cache-ttl', 'unminified-css', 'unminified-javascript', 'uses-responsive-images', 'document-title', 'html-has-lang', 'label'];
const lhr = (cles = AUDITS) => ({ lhr: {
  categories: { performance: { score: 0.914 }, accessibility: { score: 0.876 }, 'best-practices': { score: 1 }, seo: { score: 0.5 } },
  audits: { 'largest-contentful-paint': { numericValue: 2345 }, 'cumulative-layout-shift': { numericValue: 0.12345 },
    'total-blocking-time': { numericValue: 123.6 }, ...Object.fromEntries(cles.map((k, i) => [k, { score: i % 2 ? 0 : 1 }])) } } });

// Comportement du faux Chromium (et de Lighthouse) pour chaque URL.
const PAGES = {
  'https://www.a.fr/p1': { ...auQuantile(2), lh: lhr() },
  'https://www.a.fr/': { ...auQuantile(5), lh: { lhr: { ...lhr().lhr, runtimeError: { message: 'NO_FCP\ndétail' } } },
    requetes: ['pas une url', 'https://static.a.fr/x.js', 'https://cdn.shopify.com/s.js', 'https://www.google-analytics.com/g',
      'https://fonts.example.org/f.css', 'https://www.google-analytics.com/g2'],
    cookies: [{ name: '_ga', domain: '.a.fr', value: 'SECRET' }, { name: 'langue', domain: 'www.a.fr', value: 'fr' }] },
  'https://www.a.fr/c': { ...auQuantile(8), lh: { lance: 'Protocol error\npile' } },
  'https://www.a.fr/cart': { ...auQuantile(11), lh: lhr(['image-alt', 'viewport']) },
  'https://www.a.fr/contact': auQuantile(14),
  'https://www.a.fr/m': auQuantile(17),
  'https://www.a.fr/cgv': auQuantile(20),
  'https://www.a.fr/account': { final: 'https://shopify.com/authentication' },
  'https://www.a.fr/p2': { nul: true, lh: lhr(['label']) },
  'https://www.a.fr/404': { statut: 404 },
  'https://b.fr/p': { ...auQuantile(2), lh: lhr(['document-title']) },
  'https://b.fr/c': { lh: lhr() },
  'https://c.fr/': { lance: 'net::ERR_CONNECTION_REFUSED\npile', cookies: [] },
};
const IBM = [
  { ruleId: 'img_alt_valid', value: ['VIOLATION', 'FAIL'] }, { ruleId: 'img_alt_valid', value: ['VIOLATION', 'FAIL'] },
  { ruleId: 'html_lang_exists', value: ['VIOLATION', 'FAIL'] }, { ruleId: 'text_contrast', value: ['VIOLATION', 'POTENTIAL'] },
  { ruleId: 'page_title', value: ['PASS', 'PASS'] }, { ruleId: 'aria_x', value: ['RECOMMENDATION', 'FAIL'] }];

const CSV = `service,gabarit,url
A,Produit,https://www.a.fr/p1
A,Accueil,https://www.a.fr/
A,Collection,https://www.a.fr/c
A,Panier,https://www.a.fr/cart
A,Contact,https://www.a.fr/contact
A,Mentions,https://www.a.fr/m
A,CGV,https://www.a.fr/cgv
A,Compte,https://www.a.fr/account
A,Produit 2,https://www.a.fr/p2
A,Erreur,https://www.a.fr/404
B,Accueil,https://b.fr/
B,Produit,https://b.fr/p
B,Collection,https://b.fr/c
`;
const ECO_IBM = { ecoindex: { note: 'Z' }, ibm: { violations: 99 } };

if (enfant) {
  const { tmp } = preparerEnfant(mock, 'outils_page.mjs');
  const journal = { contextes: [], scripts: [], cdp: [], lighthouse: [], chrome: null, tuee: false, ferme: false, defilements: 0 };
  class Checker { async check(doc, regles) { assert.ok(doc.getElementsByTagName); assert.deepEqual(regles, ['IBM_Accessibility']); return { results: IBM }; } }
  const nouvellePage = ctx => {
    const ecouteurs = {};
    let courante = null;
    return {
      on: (ev, f) => { ecouteurs[ev] = f; },
      goto: async (url, opts) => {
        const c = PAGES[url];
        assert.equal(opts.timeout, 45000);
        ctx.cookiesPage = c.cookies ?? [];
        for (const u of c.requetes ?? []) ecouteurs.request?.({ url: () => u });
        if (c.lance) throw new Error(c.lance);
        courante = { ...c, url: c.final ?? url };
        if (ctx.cdp) for (let i = 0; i < c.req; i++) ctx.cdp({ encodedDataLength: i ? Math.floor(c.octets / c.req) : c.octets - Math.floor(c.octets / c.req) * (c.req - 1) });
        return c.nul ? null : { status: () => c.statut ?? 200 };
      },
      url: () => courante.url,
      addScriptTag: async o => journal.scripts.push(o.path),
      evaluate: async f => {
        globalThis.document = fauxDocument(courante.dom ?? 0);
        globalThis.window = { scrollTo: () => journal.defilements++, ace: { Checker } };
        return f();
      },
    };
  };
  mock.module('playwright', { namedExports: { chromium: {
    executablePath: () => '/faux/chromium',
    launch: async () => ({
      newContext: async opts => {
        journal.contextes.push(opts);
        const ctx = { cookies: async () => ctx.cookiesPage, close: async () => {} };
        ctx.newPage = async () => nouvellePage(ctx);
        ctx.newCDPSession = async () => ({ send: async m => journal.cdp.push(m), on: (ev, f) => { assert.equal(ev, 'Network.loadingFinished'); ctx.cdp = f; } });
        return ctx;
      },
      close: async () => { journal.ferme = true; },
    }),
  } } });
  mock.module('lighthouse', { defaultExport: async (url, opts) => {
    journal.lighthouse.push([url, opts]);
    const c = PAGES[url].lh;
    if (c.lance) throw new Error(c.lance);
    return c;
  } });
  mock.module('chrome-launcher', { namedExports: { launch: async opts => {
    journal.chrome = opts;
    return { port: 9333, kill: async () => { journal.tuee = true; } };
  } } });
  process.on('exit', () => writeFileSync(join(tmp, 'journal.json'), JSON.stringify(journal)));
  await import(urlScript('outils_page.mjs'));
} else {
  const fichier = `resultats/outils-${DATE}/pages.json`;

  test('traceurs, EcoIndex de A à G, IBM et Lighthouse (--audits-lighthouse)', t => {
    const r = lancer(import.meta.url, 'tous', { csv: CSV, argv: ['--audits-lighthouse'], fichiers: { [fichier]: { B: {
      traceurs: { ancien: true },
      pages: {
        'https://b.fr/': { gabarit: 'Accueil', ...ECO_IBM, lighthouse: { performance: 1, audits: {} } },
        'https://b.fr/p': { gabarit: 'Produit', ecoindex: { note: 'Z' } },
        'https://b.fr/c': { gabarit: 'Collection', ...ECO_IBM, lighthouse: { performance: 2 } },
      } } } } });
    t.after(r.nettoyer);
    assert.equal(r.statut, 0, r.erreurs);
    const res = r.json(fichier);
    const a = res.A.pages;

    assert.deepEqual(res.A.traceurs, { cookies_avant_consentement: 2,
      cookies: [{ nom: '_ga', domaine: '.a.fr' }, { nom: 'langue', domaine: 'www.a.fr' }],
      cookies_de_mesure: ['_ga'], domaines_tiers: 2, traceurs_connus: ['www.google-analytics.com'], bandeau_consentement: true });
    assert.ok(!r.lire(fichier).includes('SECRET'), 'jamais la valeur des cookies');
    assert.deepEqual(res.B.traceurs, { ancien: true });

    assert.deepEqual(a['https://www.a.fr/p1'].ecoindex, { dom: 75, requetes: 15, poids_ko: 145, score: 90, note: 'A', ges_g: 1.2, eau_cl: 1.8 });
    const notes = ['p1', '', 'c', 'cart', 'contact', 'm', 'cgv'].map(p => a[`https://www.a.fr/${p}`].ecoindex.note);
    assert.deepEqual(notes, ['A', 'B', 'C', 'D', 'E', 'F', 'G']);
    assert.deepEqual(a['https://www.a.fr/cgv'].ecoindex, { dom: 594601, requetes: 3920, poids_ko: 223216, score: 0, note: 'G', ges_g: 3, eau_cl: 4.5 });
    assert.deepEqual(a['https://www.a.fr/p1'].ibm, { violations: 3, regles: 2, par_regle: { img_alt_valid: 2, html_lang_exists: 1 }, a_verifier: 1 });
    assert.equal(a['https://www.a.fr/account'].non_teste, 'quitte le site : compte client hébergé par Shopify');
    assert.equal(a['https://www.a.fr/p2'].non_teste, 'code ?');
    assert.equal(a['https://www.a.fr/404'].non_teste, 'code 404');
    assert.equal(a['https://www.a.fr/404'].ecoindex, undefined);

    // page déjà mesurée (EcoIndex et IBM) : gardée ; page à moitié mesurée : refaite
    assert.deepEqual(res.B.pages['https://b.fr/'], { gabarit: 'Accueil', ...ECO_IBM, lighthouse: { performance: 1, audits: {} } });
    assert.equal(res.B.pages['https://b.fr/p'].ecoindex.note, 'A');
    assert.equal(res.B.pages['https://b.fr/p'].ibm.violations, 3);

    assert.deepEqual(a['https://www.a.fr/p1'].lighthouse, { performance: 91, accessibilite: 88, bonnes_pratiques: 100, seo: 50,
      lcp_s: 2.3, cls: 0.123, tbt_ms: 124, audits: Object.fromEntries(AUDITS.map((k, i) => [k, i % 2 ? 0 : 1])) });
    assert.deepEqual(a['https://www.a.fr/'].lighthouse, { erreur: 'NO_FCP' });
    assert.deepEqual(a['https://www.a.fr/c'].lighthouse, { erreur: 'Protocol error' });
    assert.deepEqual(a['https://www.a.fr/cart'].lighthouse.audits, { 'image-alt': 1, viewport: 0 });
    assert.deepEqual(a['https://www.a.fr/p2'].lighthouse.audits, { label: 1 });
    assert.equal(a['https://www.a.fr/contact'].lighthouse, undefined);
    assert.equal(a['https://www.a.fr/account'].lighthouse, undefined);
    assert.deepEqual(res.B.pages['https://b.fr/c'].lighthouse.audits['document-title'], 0);

    const j = r.json('journal.json');
    assert.deepEqual(j.lighthouse.map(l => l[0]), ['https://www.a.fr/p1', 'https://www.a.fr/', 'https://www.a.fr/c', 'https://www.a.fr/cart',
      'https://www.a.fr/p2', 'https://b.fr/p', 'https://b.fr/c']);
    assert.deepEqual(j.lighthouse[0][1], { port: 9333, output: 'json', logLevel: 'error', onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'] });
    assert.deepEqual(j.chrome, { chromePath: '/faux/chromium', chromeFlags: ['--headless=new', '--no-sandbox'] });
    assert.equal(j.tuee, true);
    assert.equal(j.ferme, true);
    assert.equal(j.scripts[0], `${RACINE_SCRIPT}node_modules/accessibility-checker-engine/ace.js`);
    assert.deepEqual(j.contextes[0], { viewport: { width: 1280, height: 900 }, locale: 'fr-FR' });
    assert.deepEqual(j.contextes[1], { viewport: { width: 1920, height: 1080 }, locale: 'fr-FR' });
    assert.ok(j.cdp.every(m => m === 'Network.enable'));
    assert.ok(j.defilements >= 16, 'défilement jusqu\'en bas (1600 px par pas de 800)');
    assert.match(r.sortie, /A \| Produit \| EcoIndex A \(90\), IBM 3 violations/);
    assert.match(r.sortie, /A \| Erreur \| code 404/);
    assert.ok(r.sortie.trim().endsWith(`resultats/outils-${DATE}/pages.json`));
  });

  test('--service : Lighthouse déjà passé sans audits, gardé sans --audits-lighthouse', t => {
    const deja = { B: { traceurs: { ancien: true }, pages: {
      'https://b.fr/': { gabarit: 'Accueil', ...ECO_IBM, lighthouse: { performance: 3 } } } } };
    const r = lancer(import.meta.url, 'service', { csv: 'service,gabarit,url\nA,Accueil,https://www.a.fr/\nB,Accueil,https://b.fr/\n',
      argv: ['--service', 'B'], fichiers: { [fichier]: deja } });
    t.after(r.nettoyer);
    assert.equal(r.statut, 0, r.erreurs);
    assert.deepEqual(r.json(fichier), deja);
    assert.deepEqual(r.json('journal.json').lighthouse, []);
  });

  test('--sans-lighthouse et site injoignable : traceurs et pages en erreur', t => {
    const r = lancer(import.meta.url, 'injoignable', { csv: 'service,gabarit,url\nC,Accueil,https://c.fr/\n', argv: ['--sans-lighthouse'] });
    t.after(r.nettoyer);
    assert.equal(r.statut, 0, r.erreurs);
    assert.deepEqual(r.json(fichier), { C: { traceurs: { erreur: 'net::ERR_CONNECTION_REFUSED' },
      pages: { 'https://c.fr/': { gabarit: 'Accueil', non_teste: 'net::ERR_CONNECTION_REFUSED' } } } });
    const j = r.json('journal.json');
    assert.equal(j.chrome, null);
    assert.equal(j.ferme, true);
  });
}
