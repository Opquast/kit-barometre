// Tests de scripts/sources_tiers.mjs : Playwright, Alfa, Sa11y (injecté), moteur Opquast (faux fichiers) et
// pdftotext simulés ; html-validate est le vrai. Sorties dans un dossier temporaire, « hors dépôt » compris.
import { test, mock } from 'node:test';
import assert from 'node:assert/strict';
import * as cp from 'node:child_process';
import { mkdirSync, writeFileSync, readFileSync, existsSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { lancer, executerScenario, aujourdhui } from './aide_parcours.mjs';

const CSV = `service,gabarit,url
Boutique A,Accueil,https://a.fr/
Boutique A,Produit,https://a.fr/products/p
Boutique A,Page,https://a.fr/pages/x
Boutique A,Collection,https://a.fr/collections/vide
Boutique B,Compte,https://b.fr/account
Boutique B,Erreur,https://b.fr/404
Boutique B,Vide,https://b.fr/vide
Boutique B,Robot,https://b.fr/robot
Boutique B,Crash,https://b.fr/crash
Boutique B,Crash2,https://b.fr/crash2
Boutique C,Accueil,https://c.fr/`;

const LIBS = ['jquery-3.7.1.min.js', 'jquery-migrate-3.5.2.min.js', 'oqs-utils.js', 'cssParser.js', 'oqs-validator.js', 'oqs-tests.js', 'oqs-tests-overlay.js'];
function moteur(tmp) {
  const engine = join(tmp, 'moteur/public/engine');
  mkdirSync(engine, { recursive: true }); mkdirSync(join(tmp, 'moteur/data'), { recursive: true });
  for (const f of LIBS) writeFileSync(join(engine, f), `/* ${f} */ window.__${f.replace(/\W/g, '_')} = 1;`);
  writeFileSync(join(engine, 'rules.json'), JSON.stringify({ 'test-1': { nom: 'titre' } }));
  writeFileSync(join(engine, 'rulesets.json'), JSON.stringify({ 'oq-1': ['test-1'], 'oq-2': [], 'oq-12': [], 'oq-x': [] }));
  writeFileSync(join(tmp, 'moteur/data/v5-automation-triage.json'), JSON.stringify({ rules: [{ id: 'oq-1', num: '5' }, { id: 'oq-2', num: '7' }, { id: 'oq-12', num: '12' }] }));
  return engine;
}

const SYNTHESE = [
  { id: 'oq-1', result: 'c', details: [{ comment: 'Titre présent' }] },
  { criterion: 'oq-2', result: 'nc', details: [{ text: 't' }, {}] },
  { result: 'na' },
  { id: 'oq-1', result: 'i', details: [] },
  { id: 'oq-2', result: 'na', details: [{ message: 'm' }] },
  { id: 'oq-1', result: 'nc', details: [{}] },
  { id: 'oq-2', result: 'c' },
];
// Faux moteur Opquast : appelle toutes les briques que le script installe (Q, console.exception, dnsLookup, XHR).
const opquast = (synthese, attente = false) => (w, page) => {
  w.jQuery = { extractPageInfo: () => ({ titre: w.document.title }) };
  w.analyze = async subset => {
    const g = w;
    if (attente) return new Promise(() => {});
    const d = g.Q.defer(); d.resolve(1); await d.promise;
    const d2 = g.Q.defer(); d2.reject(new Error('x')); await d2.promise.catch(() => {});
    await g.Q.resolve(2); await g.Q.reject(new Error('y')).catch(() => {});
    const tous = await g.Q.promised()(Promise.resolve(1), 2);
    g.console.exception(new Error('z'));
    const dns = await g.dnsLookup('a.fr');
    const x = await g.XHR.get('https://a.fr/'); const q = await g.XHR.query('https://a.fr/');
    page.j.push(['analyze', Object.keys(subset), Object.keys(g.tests), tous, dns, x.status, x.getHeader('server'), q.status,
      typeof g.sidecar.plainText, g.sidecar.pageInfo.titre, document.head.querySelectorAll('script').length]);
    return 'brut';
  };
  w.synthesize_results = () => synthese;
};
const sa11y = resultats => (o, page) => {
  if (!o.path.endsWith('sa11y.umd.min.js')) return;
  const w = page.courant.win;
  w.Sa11yLangFr = { strings: { bonjour: 'Bonjour' } };
  w.Sa11y = { Lang: { addI18n: s => page.j.push(['i18n', Object.keys(s)]) },
    Sa11y: class { constructor(opt) { page.j.push(['sa11y', opt]); if (resultats) setTimeout(() => { w.sa11yCheckComplete = { results: resultats }; }, 250); } } };
};
const issue = (k, outcome) => ({ toJSON: () => ({ rule: { uri: `https://alfa.siteimprove.com/rules/${k}` }, outcome }) });
const ALFA = {
  'https://a.fr/': () => Promise.resolve([issue('sia-r62', 'failed'), issue('sia-r62', 'passed'), issue('sia-r65', 'passed'),
    issue('sia-r41', 'inapplicable'), issue('sia-r1', 'inapplicable'), issue('sia-r1', 'cantTell')]),
  'https://a.fr/products/p': () => new Promise(() => {}),
  'https://a.fr/pages/x': () => Promise.reject(new Error('alfa en échec')),
  'https://a.fr/collections/vide': () => Promise.resolve([issue('sia-r65', 'cantTell')]),
};
const MENU = '<header><nav><a>Accueil</a><a>Accueil</a><a>Boutique</a><a>Contact</a><a> À propos </a><a>Le</a><a>Un lien beaucoup trop long pour un menu</a></nav></header>';
const PAGES = {
  'https://a.fr/': { html: `<html><head><title>Accueil A</title></head><body>${MENU}<main><p>Bienvenue</p></main><button>Tout refuser</button></body></html>`,
    preparer: opquast(SYNTHESE), sa11y: [{ test: 'LINK_STOPWORD' }, { type: 'QA_UNDERLINE' }, { test: 'LINK_STOPWORD' }, { test: 'AUTRE' }] },
  'https://a.fr/products/p': { html: `<html><head><title>Produit</title></head><body>${MENU}<p>Fiche</p></body></html>`,
    preparer: (w, page) => { w.console.exception = () => {}; opquast({ pas: 'un tableau' })(w, page); }, sa11y: null },
  'https://a.fr/pages/x': { preparer: w => w.document.body.remove() },
  'https://a.fr/collections/vide': { html: '<html><head><title>Collection</title></head><body></body></html>', preparer: opquast([], true), sa11y: [] },
  'https://b.fr/account': { finale: 'https://shopify.com/1/account' },
  'https://b.fr/404': { status: 404 },
  'https://b.fr/vide': { status: null },
  'https://b.fr/robot': { title: 'Just a moment...' },
  'https://b.fr/crash': { erreur: 'Target page, context or browser has been closed\nlog' },
  'https://b.fr/crash2': { erreur: 'browser has crashed' },
};
const REQ = {
  'https://a.fr/': { status: 200, html: '<!doctype html><html lang="fr"><head><title></title></head><body><img src="a.png"><img src="b.png"><p>ok</p></body></html>' },
  'https://a.fr/pages/x': { status: 200, url: 'https://cdn.autre.fr/x', html: '<p>' },
  'https://a.fr/collections/vide': { status: 200, html: '<!doctype html><html lang="fr"><head><title>Collection</title></head><body><p>x</p></body></html>' },
};

function site({ contexteRate = 0, fermeturesRatees = 0, ctxFermetureRatee = 0 } = {}) {
  return {
    page: url => PAGES[url] ?? {},
    nouveauContexte: n => { if (n === contexteRate) throw new Error('navigateur indisponible'); },
    fermeture: n => { if (n <= fermeturesRatees) throw new Error('déjà fermé'); },
    fermerContexte: n => { if (n === ctxFermetureRatee) throw new Error('contexte perdu'); },
    compte: (d, page) => (d.filtre && page.url() === 'https://a.fr/' ? 1 : 0),
    clic: () => Promise.reject(new Error('bouton masqué')),
    touche: (k, page) => (k === 'Escape' && page.url() === 'https://a.fr/' ? Promise.reject(new Error('page fermée')) : undefined),
    capture: (o, page) => (page.url() === 'https://a.fr/' ? Promise.reject(new Error('capture impossible')) : undefined),
    script: (o, page) => ('sa11y' in page.courant ? sa11y(page.courant.sa11y)(o, page) : undefined),
  };
}

function mocks(m, j) {
  m.module('node:child_process', { namedExports: { ...cp, spawnSync: (cmd, args) => {
    j.push(['spawn', cmd, args]);
    if (cmd === 'pdftotext') return { stdout: args[1].endsWith('Boutique_A__Accueil.pdf') ? 'ACCUEIL\nContact\n' : null };
    return { status: 0 };
  } } });
  m.module('@siteimprove/alfa-playwright', { namedExports: { Playwright: { toPage: async h => ({ url: h.valeur.URL }) } } });
  m.module('@siteimprove/alfa-rules', { defaultExport: ['sia-r62', 'sia-r65', 'sia-r41', 'sia-r1', 'sia-r2'].map(k => ({ uri: `https://alfa.siteimprove.com/rules/${k.toUpperCase()}` })) });
  m.module('@siteimprove/alfa-act', { namedExports: { Audit: { of: (p, regles) => {
    j.push(['audit', p.url, regles.map(r => r.uri.split('/').pop())]);
    return { evaluate: ALFA[p.url] ?? (() => Promise.resolve([])) };
  } } } });
}

const requete = j => ({ newContext: async o => {
  j.push(['requestContext', o.userAgent]);
  return {
    get: async url => { j.push(['get', url]); const d = REQ[url] ?? { status: 404 }; return { status: () => d.status, url: () => d.url ?? url, text: async () => d.html ?? '' }; },
    dispose: async () => { j.push(['dispose']); },
  };
} });

const SCENARIOS = {
  complet: tmp => ({ csv: CSV, args: [moteur(tmp), join(tmp, 'hors')], site: site({ contexteRate: 1, fermeturesRatees: 2, ctxFermetureRatee: 3 }), mocks, request: requete }),
  reprise: tmp => ({ csv: CSV, args: [moteur(tmp), join(tmp, 'hors'), '--service', 'Boutique A'], site: site(), mocks, request: requete }),
};

if (process.env.AIDE_SCENARIO) {
  const tmp = process.env.AIDE_TMP;
  await executerScenario(mock, 'sources_tiers.mjs', SCENARIOS[process.env.AIDE_SCENARIO](tmp));
} else {
  const fichier = `resultats/sources-${aujourdhui()}/tiers.json`;
  const HV = 'html-validate', OQ = 'Moteur Opquast devtools', SA = 'Sa11y', AL = 'Siteimprove Alfa';

  test('sources_tiers : html-validate, moteur Opquast, Sa11y, Alfa, impression et pages non testées', () => {
    const r = lancer(import.meta.url, 'complet');
    assert.equal(r.status, 0, r.stderr);
    const t = JSON.parse(r.lire(fichier));
    const a = t['Boutique A']['https://a.fr/'];
    assert.equal(a._gabarit, 'Accueil');
    assert.deepEqual(a['117'], [['C', 'wcag/h30 : aucun défaut', HV]]);
    assert.deepEqual(a['118'], [['NC', 'wcag/h37 : 2 défaut(s), ex. « <img> is missing required "alt" attribute »', HV]]);
    assert.deepEqual(a['103'], [['NC', 'empty-title : 1 défaut(s), ex. « <title> cannot be empty, must have text content »', HV], ['C', 'long-title : aucun défaut', HV]]);
    for (const n of ['126', '159', '172']) assert.equal(a[n][0][0], 'C');
    assert.deepEqual(a['5'], [['C', 'Moteur Opquast (jeu oq-1) : c, 1 élément(s) ; Titre présent', OQ], ['NC', 'Moteur Opquast (jeu oq-1) : nc, 1 élément(s)', OQ]]);
    assert.deepEqual(a['7'], [['NC', 'Moteur Opquast (jeu oq-2) : nc, 2 élément(s) ; t', OQ], ['NA', 'Moteur Opquast (jeu oq-2) : na, 1 élément(s) ; m', OQ],
      ['C', 'Moteur Opquast (jeu oq-2) : c', OQ]]);
    assert.deepEqual(a['137'], [['NC', 'Sa11y : LINK_STOPWORD 2, LINK_CLICK_HERE 0', SA], ['NA', 'Alfa SIA-R41 : inapplicable 1', AL]]);
    assert.deepEqual(a['139'], [['NC', 'Sa11y : QA_UNDERLINE 1', SA]]);
    assert.deepEqual(a['192'], [['C', 'Sa11y : QA_UPPERCASE 0', SA]]);
    assert.deepEqual(a['235'], [['C', 'Sa11y : QA_FAKE_LIST 0', SA]]);
    assert.deepEqual(a['140'], [['NC', 'Alfa SIA-R62 : failed 1, passed 1', AL]]);
    assert.deepEqual(a['165'], [['C', 'Alfa SIA-R65 : passed 1', AL]]);
    assert.equal(a['12'], undefined, 'jeu hors sujet ignoré');
    assert.deepEqual(a['196'], [['NC', '2 libellé(s) du menu d\'en-tête sur 4 dans le PDF imprimé (cookies refusés) : Accueil, Contact', 'Impression PDF (cookies refusés)']]);

    const p = t['Boutique A']['https://a.fr/products/p'];
    assert.deepEqual(p, { _gabarit: 'Produit', 196: [['C', '0 libellé(s) du menu d\'en-tête sur 4 dans le PDF imprimé (cookies refusés)', 'Impression PDF (cookies refusés)']] });
    assert.deepEqual(t['Boutique A']['https://a.fr/pages/x'], { _gabarit: 'Page', _opquast: 'Cannot read properties of undefined (reading \'extractPageInfo\')' });
    const c = t['Boutique A']['https://a.fr/collections/vide'];
    assert.equal(c._opquast, 'moteur Opquast : délai dépassé');
    assert.deepEqual(c['118'], [['C', 'wcag/h37 : aucun défaut', HV]]);
    assert.deepEqual(c['137'], [['C', 'Sa11y : LINK_STOPWORD 0, LINK_CLICK_HERE 0', SA]]);
    assert.equal(c['165'], undefined, 'Alfa « cantTell » seul : pas de verdict');

    const b = t['Boutique B'];
    assert.deepEqual(Object.fromEntries(Object.entries(b).map(([u, v]) => [u, v._non_teste])), {
      'https://b.fr/account': 'quitte le site (compte client hébergé par Shopify)',
      'https://b.fr/404': 'code 404', 'https://b.fr/vide': 'code ?',
      'https://b.fr/robot': 'vérification anti-robot affichée : non contournée',
      'https://b.fr/crash': 'Target page, context or browser has been closed', 'https://b.fr/crash2': 'browser has crashed' });
    assert.deepEqual(t['Boutique C']['https://c.fr/'], { _gabarit: 'Accueil', _opquast: 'Cannot read properties of undefined (reading \'extractPageInfo\')' });

    // moteur : jeux retenus (sans hors-sujet ni jeu inconnu), bibliothèques injectées puis retirées
    const an = r.journal.find(x => x[0] === 'analyze');
    assert.deepEqual(an, ['analyze', ['oq-1', 'oq-2'], ['test-1'], [1, 2], null, 0, null, 0, 'string', 'Accueil A', 0]);
    assert.deepEqual(r.journal.find(x => x[0] === 'i18n'), ['i18n', ['bonjour']]);
    assert.deepEqual(r.journal.find(x => x[0] === 'sa11y')[1], { headless: true, checkRoot: 'body', detectSPArouting: false });
    assert.deepEqual(r.journal.find(x => x[0] === 'audit')[2], ['SIA-R62', 'SIA-R65', 'SIA-R41', 'SIA-R1']);
    // seul clic : le refus des cookies
    assert.deepEqual(r.journal.filter(x => x[0] === 'clic').map(x => x[1]), ['https://a.fr/']);
    // DOM et PDF hors dépôt, impression convertie
    const hors = join(r.tmp, 'hors');
    assert.match(readFileSync(join(hors, 'dom/Boutique_A__Accueil.html'), 'utf8'), /Bienvenue/);
    assert.ok(existsSync(join(hors, 'Boutique_A__Accueil.pdf')));
    assert.deepEqual(r.journal.find(x => x[0] === 'spawn')[2], ['-f', '1', '-l', '1', '-r', '45', '-jpeg', join(hors, 'Boutique_A__Accueil.pdf'), join(hors, 'captures/Boutique_A__Accueil__impression')]);
    // contexte refusé puis deux plantages : trois relances, fermeture finale
    assert.equal(r.journal.filter(x => x[0] === 'launch').length, 4);
    assert.deepEqual(r.journal.slice(-2).map(x => x[0]), ['close', 'dispose']);
    assert.match(r.stdout, /Boutique A \| Page \| {2}\(opquast : Cannot read/);
    assert.match(r.stdout, /Boutique B \| Erreur \| code 404/);
    assert.match(r.stdout, /tiers\.json/);
  });

  test('sources_tiers : reprise d\'un fichier existant, seules les pages non testées sont refaites', () => {
    const tmp = mkdtempSync(join(tmpdir(), 'kit-js-'));
    const f = join(tmp, fichier);
    mkdirSync(join(f, '..'), { recursive: true });
    const avant = {
      'Boutique A': {
        'https://a.fr/': { _gabarit: 'Accueil', 5: [['C', 'déjà relevé', 'x']] },
        'https://a.fr/products/p': { _gabarit: 'Produit', _non_teste: 'code 404' },
        'https://a.fr/pages/x': { _gabarit: 'Page' }, 'https://a.fr/collections/vide': { _gabarit: 'Collection' },
      },
      'Boutique B': { 'https://b.fr/404': { _gabarit: 'Erreur', _non_teste: 'code 404' } },
    };
    writeFileSync(f, JSON.stringify(avant));
    const r = lancer(import.meta.url, 'reprise', tmp);
    assert.equal(r.status, 0, r.stderr);
    const t = JSON.parse(r.lire(fichier));
    assert.deepEqual(t['Boutique A']['https://a.fr/'], avant['Boutique A']['https://a.fr/']);
    assert.deepEqual(t['Boutique B'], avant['Boutique B'], 'autre service conservé tel quel');
    assert.equal(t['Boutique A']['https://a.fr/products/p']._non_teste, undefined);
    assert.equal(t['Boutique A']['https://a.fr/products/p']['196'][0][0], 'C');
    assert.deepEqual(r.journal.filter(x => x[0] === 'goto').map(x => x[1]), ['https://a.fr/products/p']);
  });
}
