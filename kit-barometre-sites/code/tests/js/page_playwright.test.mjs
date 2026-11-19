// Tests de scripts/page_playwright.mjs : Playwright remplacé par un faux navigateur, aucun site réel.
import { test, mock } from 'node:test';
import assert from 'node:assert/strict';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { enfant, lancer, preparerEnfant, urlScript, DATE } from './aide_outils.mjs';

// Comportement du faux navigateur pour chaque URL.
const PAGES = {
  'https://a.fr/': { corps: '<html><head><meta charset="utf-8"><meta http-equiv="Content-Type" content="text/html"></head></html>',
    resultats: { 1: ['conforme', 'ok'], 2: ['conforme', 'ok'], 3: ['non-applicable', ''] } },
  'https://a.fr/p': { corps: '<p>sans meta é</p>', resultats: { 1: ['conforme', 'ok'], 2: ['non-conforme', 'manque'], 3: ['non-applicable', ''] } },
  'https://a.fr/account': { final: 'https://shopify.com/compte' },
  'https://a.fr/vide': { nul: true },
  'https://a.fr/404': { statut: 404 },
  'https://a.fr/panne': { lance: 'délai dépassé\npile' },
  'https://b.fr/': { rejet: true, resultats: { 1: ['conforme', ''], 4: ['non-conforme', 'x'] } },
  'https://b.fr/p': { corps: '<meta charset=utf-8>', resultats: { 1: ['non-conforme', ''], 4: ['conforme', ''] } },
};

const CSV = `service,gabarit,url
A,Accueil,https://a.fr/
A,"Fiche ""produit""",https://a.fr/p
A,"Compte, client",https://a.fr/account
A,Vide,https://a.fr/vide
A,Erreur,https://a.fr/404
A,Panne,https://a.fr/panne
B,Accueil,https://b.fr/
B,Produit,https://b.fr/p
`;

if (enfant) {
  const { tmp } = preparerEnfant(mock, 'page_playwright.mjs');
  const journal = { brut: {}, evenements: [] };
  let courante = null;
  const page = {
    goto: async url => {
      const c = PAGES[url];
      journal.evenements.push(['goto', url]);
      if (c.lance) throw new Error(c.lance);
      courante = c.final ?? url;
      if (c.nul) return null;
      return { status: () => c.statut ?? 200, text: async () => { if (c.rejet) throw new Error('corps illisible'); return c.corps; } };
    },
    url: () => courante,
    evaluate: async (f, arg) => {
      if (typeof f === 'string') return { version: 'controles-test-1.0', resultats: PAGES[courante].resultats, script: f.length };
      globalThis.window = {};
      f(arg);
      journal.brut[courante] = globalThis.window.__BRUT;
    },
  };
  mock.module('playwright', { namedExports: { chromium: {
    launch: async () => ({
      newContext: async opts => { journal.evenements.push(['contexte', opts]); return { newPage: async () => page }; },
      close: async () => journal.evenements.push(['fermeture']),
    }),
  } } });
  process.on('exit', () => writeFileSync(join(tmp, 'journal.json'), JSON.stringify(journal)));
  await import(urlScript('page_playwright.mjs'));
} else {
  const dossier = `resultats/page-${DATE}`;

  test('tous les écrans : résultats, non testés et rapport', t => {
    const r = lancer(import.meta.url, 'tous', { csv: CSV });
    t.after(r.nettoyer);
    assert.equal(r.statut, 0, r.erreurs);
    const { meta, services } = r.json(`${dossier}/resultats.json`);
    assert.equal(meta.controles, 'controles-test-1.0');
    assert.equal(meta.script, 'scripts/page_playwright.mjs');
    assert.deepEqual(Object.keys(services), ['A', 'B']);
    const [accueil, fiche, compte, vide, erreur, panne] = services.A.pages;
    assert.equal(fiche.gabarit, 'Fiche "produit"');
    assert.equal(compte.gabarit, 'Compte, client');
    assert.equal(accueil.statut_http, 200);
    assert.equal(accueil.url_finale, 'https://a.fr/');
    assert.deepEqual(accueil.controles[1], { rule_number: 2, status: 'conforme', comment: 'ok', evidence: '' });
    assert.equal(fiche.controles.filter(c => c.status === 'non-conforme').length, 1);
    assert.equal(compte.non_teste, 'quitte le site (shopify.com) : compte client hébergé par Shopify');
    assert.deepEqual(compte.controles, []);
    assert.equal(vide.non_teste, 'code aucune réponse');
    assert.equal(vide.statut_http, null);
    assert.equal(erreur.non_teste, 'code 404');
    assert.equal(erreur.statut_http, 404);
    assert.equal(panne.non_teste, 'délai dépassé');
    assert.equal(services.B.pages.length, 2);

    // octets du code source brut transmis à controles_page.js (règle 232)
    const { brut, evenements } = r.json('journal.json');
    const corps = PAGES['https://a.fr/'].corps;
    assert.deepEqual(brut['https://a.fr/'], { taille: Buffer.byteLength(corps), fin_meta_charset: corps.indexOf('<meta http') , declarations: 2 });
    assert.deepEqual(brut['https://a.fr/p'], { taille: Buffer.byteLength('<p>sans meta é</p>'), fin_meta_charset: null, declarations: 0 });
    assert.deepEqual(brut['https://b.fr/'], { taille: 0, fin_meta_charset: null, declarations: 0 });
    assert.deepEqual(brut['https://b.fr/p'], { taille: 20, fin_meta_charset: 20, declarations: 1 });
    assert.deepEqual(evenements[0], ['contexte', { viewport: { width: 1280, height: 900 }, locale: 'fr-FR' }]);
    assert.deepEqual(evenements.at(-1), ['fermeture']);

    const md = r.lire(`${dossier}/rapport.md`).split('\n');
    assert.equal(md[0], `# Contrôles du code de la page (controles-test-1.0) du ${DATE}`);
    assert.ok(md.includes('| Règle | A | B |'));
    assert.ok(md.includes('|---|---|---|'));
    assert.ok(md.includes('| 1 | C (2) | **1 NC** / 2 |'));
    assert.ok(md.includes('| 2 | **1 NC** / 2 |  |'));
    assert.ok(md.includes('| 3 | non-applicable |  |'));
    assert.ok(md.includes('| 4 |  | **1 NC** / 2 |'));
    assert.ok(md.includes('- A, Compte, client : non testé (quitte le site (shopify.com) : compte client hébergé par Shopify).'));
    assert.ok(md.includes('- A, Panne : non testé (délai dépassé).'));
    assert.equal(md.filter(l => l.startsWith('- ')).length, 4);
    assert.match(r.sortie, /A \| Fiche "produit" \| 3 règles, 1 non conformes/);
    assert.match(r.sortie, /A \| Erreur \| non testé : code 404/);
    assert.match(r.sortie, /: 8 écrans/);
  });

  test('--service ne garde que les écrans du service demandé', t => {
    const r = lancer(import.meta.url, 'service', { csv: CSV, argv: ['--service', 'B'] });
    t.after(r.nettoyer);
    assert.equal(r.statut, 0, r.erreurs);
    const { services } = r.json(`${dossier}/resultats.json`);
    assert.deepEqual(Object.keys(services), ['B']);
    assert.deepEqual(services.B.pages.map(p => p.url), ['https://b.fr/', 'https://b.fr/p']);
    assert.ok(r.lire(`${dossier}/rapport.md`).includes('| 4 | **1 NC** / 2 |'));
    assert.match(r.sortie, /: 2 écrans/);
  });
}
