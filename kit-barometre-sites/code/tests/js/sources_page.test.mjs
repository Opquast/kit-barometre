// Tests de scripts/sources_page.mjs : chaque scénario tourne dans un processus enfant (voir aide_releve.mjs).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { lancer, installer, csv, DATE, RACINE_SCRIPT } from './aide_releve.mjs';

const MENU2 = '<header><nav><a href="/">Accueil</a><a href="/n">Nouveautés</a><a href="/n2">Nouveautés</a><a href="/a">Abc</a><a href="/l">Un libellé de menu beaucoup trop long</a></nav></header>';
const MENU4 = '<nav aria-label="Principal"><a href="/1">Soins visage</a><a href="/2">Maquillage</a><a href="/3">Parfums</a></nav><header><a href="/collections/cadeaux">Cadeaux</a></header>';

// résultats axe-core et IBM simulés selon la page analysée
const AXE = {
  'https://x.test/products/p': {
    violations: [{ id: 'link-in-text-block', nodes: [1, 2] }, { id: 'image-alt', nodes: [1] }],
    passes: [{ id: 'image-alt', nodes: [1, 2, 3] }, { id: 'document-title', nodes: [1] }],
    incomplete: [{ id: 'tabindex', nodes: [1] }, { id: 'document-title', nodes: [1] }],
    inapplicable: [{ id: 'blink' }, { id: 'image-alt' }],
  },
};
const IBM = {
  'https://x.test/products/p': [
    { ruleId: 'select_options_grouped', value: ['VIOLATION', 'FAIL'] }, { ruleId: 'img_alt_valid', value: ['', 'PASS'] },
    { ruleId: 'a_text_purpose', value: ['', 'POTENTIAL'] }, { ruleId: 'a_text_purpose', value: ['', 'MANUAL'] },
    { ruleId: 'page_title_valid', value: ['', 'RECOMMENDATION'] }, { ruleId: 'regle_hors_liste', value: ['', 'FAIL'] },
  ],
};
const vide = { violations: [], passes: [], incomplete: [], inapplicable: [] };
const outils = {
  axe: { run: async (doc, o) => { assert.equal(o.runOnly.type, 'rule'); return AXE[doc.location.href] || vide; } },
  ace: { Checker: class { async check(doc, p) { assert.deepEqual(p, ['IBM_Accessibility']); return { results: IBM[doc.location.href] || [] }; } } },
};
function pdftotext(sorties) { let i = 0; return (cmd, a) => { assert.equal(cmd, 'pdftotext'); assert.equal(a[0], '-layout'); return { stdout: sorties[i++] }; }; }

export const scenarios = {
  principal: {
    csv: csv([
      ['X', 'Accueil', 'https://x.test/'], ['X', 'Produit', 'https://x.test/products/p'], ['X', 'Collection', 'https://x.test/collections/all'],
      ['Y', 'Accueil', 'https://y.test/'], ['Y', 'Produit', 'https://y.test/p'], ['Y', 'Blog', 'https://y.test/blog'],
      ['Z', 'Accueil', 'https://z.test/'], ['Z', 'Produit', 'https://z.test/p'], ['Z', 'Accueil (bis)', 'https://z.test/?v=2,3'],
      ['W', 'Collection', 'https://w.test/c'],
    ]),
    ...outils,
    spawnSync: pdftotext(['ACCUEIL\n NOUVEAUTÉS', undefined, 'Soins visage\n']),
    contexteEchoue: (n, k) => n === 1 && k === 2,  // 2e contexte du 1er navigateur
    fermetureEchoue: n => n < 3,
    pages: {
      'https://x.test/products/p': { html: `<title>Crème</title><body>${MENU2}<p>Fiche</p></body>`, popups: ['https://pub.test/1', 'https://pub.test/2'], captureErreur: true },
      'https://x.test/collections/all': { html: '<body>x</body>', finale: 'https://compte.shopify.test/login' },
      'https://y.test/': { statut: null },
      'https://y.test/p': { statut: 404 },
      'https://y.test/blog': { html: '<title>Just a moment...</title><body></body>' },
      'https://z.test/': { erreur: 'Target page, context or browser has been closed' },
      'https://z.test/p': { html: '<body><p>Produit</p></body>' },
      'https://z.test/?v=2,3': { html: `<body>${MENU4}</body>` },
      'https://w.test/c': { html: '<body>Collection</body>', preparer: w => w.document.body.remove(), ctxFermetureEchoue: true },
    },
  },
  seul: {
    csv: csv([['X', 'Accueil', 'https://x.test/'], ['Z', 'Blog', 'https://z.test/blog']]),
    ...outils,
    spawnSync: () => { throw new Error('pas de PDF attendu'); },
    pages: { 'https://z.test/blog': { html: '<body></body>' } },
  },
};

if (process.env.AIDE_NOM) await installer(scenarios[process.env.AIDE_NOM]);
else {
  const sortie = `resultats/sources-${DATE()}/pages.json`;
  test('sources_page : popups, axe-core, IBM, impression PDF, erreurs et relances du navigateur', () => {
    const deja = { X: { 'https://x.test/': { _gabarit: 'Accueil', 154: [['C', 'déjà', 'x']] }, 'https://x.test/products/p': { _non_teste: 'ancien' } } };
    const r = lancer(import.meta.url, 'sources_page.mjs', 'principal', {
      env: t => ({ CAPTURES: join(t, 'captures') }),
      avant: t => { mkdirSync(join(t, `resultats/sources-${DATE()}`), { recursive: true }); writeFileSync(join(t, sortie), JSON.stringify(deja)); },
    });
    try {
      assert.equal(r.statut, 0, r.erreurs);
      const j = r.lire(sortie);
      assert.deepEqual(j.X['https://x.test/'], deja.X['https://x.test/']);
      const p = j.X['https://x.test/products/p'];
      assert.equal(p._gabarit, 'Produit');
      assert.deepEqual(p['154'], [['NC', '2 fenêtre(s) ouverte(s) au chargement : https://pub.test/1, https://pub.test/2', 'Playwright (événements popup)']]);
      assert.deepEqual(p['140'], [['NC', 'link-in-text-block : 2 échec(s), 0 réussi(s), 0 à vérifier', 'axe-core']]);
      assert.deepEqual(p['118'], [['NC', 'image-alt : 1 échec(s), 3 réussi(s), 0 à vérifier', 'axe-core'], ['C', 'img_alt_valid : 0 échec(s), 1 réussi(s), 0 à vérifier', 'IBM Equal Access']]);
      assert.deepEqual(p['167'], [['I', 'tabindex : 0 échec(s), 0 réussi(s), 1 à vérifier', 'axe-core']]);
      assert.equal(p['103'][0][0], 'C'); assert.deepEqual(p['103'][1], ['NA', 'page_title_valid : 0 échec(s), 0 réussi(s), 0 à vérifier', 'IBM Equal Access']);
      assert.deepEqual(p['126'][0], ['NA', 'blink : 0 échec(s), 0 réussi(s), 0 à vérifier', 'axe-core']);
      assert.deepEqual(p['93'], [['NC', 'select_options_grouped : 1 échec(s), 0 réussi(s), 0 à vérifier', 'IBM Equal Access']]);
      assert.deepEqual(p['117'], [['I', 'a_text_purpose : 0 échec(s), 0 réussi(s), 2 à vérifier', 'IBM Equal Access']]);
      assert.deepEqual(p['196'], [['NC', '2 libellé(s) du menu sur 2 retrouvé(s) dans le PDF imprimé : Accueil, Nouveautés', 'Chromium page.pdf + pdftotext']]);
      assert.equal(j.X['https://x.test/collections/all']._non_teste, 'quitte le site (compte client hébergé par Shopify)');
      assert.equal(j.Y['https://y.test/']._non_teste, 'code ?');
      assert.equal(j.Y['https://y.test/p']._non_teste, 'code 404');
      assert.equal(j.Y['https://y.test/blog']._non_teste, 'vérification anti-robot affichée : non contournée');
      assert.equal(j.Z['https://z.test/']._non_teste, 'Target page, context or browser has been closed');
      assert.deepEqual(j.Z['https://z.test/p']['196'], [['I', '0 libellé(s) du menu sur 0 retrouvé(s) dans le PDF imprimé', 'Chromium page.pdf + pdftotext']]);
      assert.deepEqual(j.Z['https://z.test/p']['154'], [['C', 'Aucune nouvelle fenêtre ouverte pendant le chargement et 6 s après', 'Playwright (événements popup)']]);
      assert.deepEqual(j.Z['https://z.test/?v=2,3']['196'], [['C', '1 libellé(s) du menu sur 4 retrouvé(s) dans le PDF imprimé : Soins visage', 'Chromium page.pdf + pdftotext']]);
      assert.equal(j.W['https://w.test/c']['196'], undefined);
      assert.equal(j.W['https://w.test/c']['154'][0][0], 'C');
      // navigateur relancé après l'échec du contexte, puis après la fermeture de la cible ; fermé à la fin
      assert.deepEqual(r.journal.filter(x => x[0] === 'launch').map(x => x[1]), [1, 2, 3]);
      assert.deepEqual(r.journal.filter(x => x[0] === 'nav.close').map(x => x[1]), [1, 2, 3]);
      assert.deepEqual(r.journal.find(x => x[0] === 'newContext')[2], { viewport: { width: 1280, height: 900 }, locale: 'fr-FR' });
      assert.deepEqual(r.journal.filter(x => x[0] === 'script').map(x => x[1].slice(RACINE_SCRIPT.length)).slice(0, 2), ['node_modules/axe-core/axe.min.js', 'node_modules/accessibility-checker-engine/ace.js']);
      // captures pleine page et haut de page dans CAPTURES (hors dépôt), nom de fichier nettoyé ; échec de capture toléré
      const captures = r.journal.filter(x => x[0] === 'capture').map(x => x[1].slice(r.tmp.length));
      assert.deepEqual(captures, ['/captures/X__Produit.jpg', '/captures/X__Produit__haut.jpg', '/captures/Z__Produit.jpg', '/captures/Z__Produit__haut.jpg',
        '/captures/Z__Accueil_bis_.jpg', '/captures/Z__Accueil_bis___haut.jpg', '/captures/W__Collection.jpg', '/captures/W__Collection__haut.jpg']);
      assert.ok(r.existe('captures'));
      assert.equal(r.journal.filter(x => x[0] === 'pdf').length, 3);
      assert.ok(!r.existe(`resultats/sources-${DATE()}/.pdf`));  // dossier des PDF supprimé
      assert.match(r.sortie, /^X \| Produit \| 14:NA 93:NC 103:C\/NA 117:I 118:NC\/C 126:NA\/NA 140:NC 154:NC 165:NA 166:NA 167:I 172:NA 189:NA 196:NC 245:NA$/m);
      assert.match(r.sortie, /^Y \| Accueil \| code \?$/m);
    } finally { r.nettoyer(); }
  });

  test('sources_page : --service ne traite que ce site, fichier du jour créé', () => {
    const r = lancer(import.meta.url, 'sources_page.mjs', 'seul', { args: () => ['--service', 'Z'] });
    try {
      assert.equal(r.statut, 0, r.erreurs);
      const j = r.lire(sortie);
      assert.deepEqual(Object.keys(j), ['Z']);
      assert.equal(j.Z['https://z.test/blog']._gabarit, 'Blog');
      assert.ok(!r.journal.some(x => x[0] === 'spawn'));
    } finally { r.nettoyer(); }
  });
}
