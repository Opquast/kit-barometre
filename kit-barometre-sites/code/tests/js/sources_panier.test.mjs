// Tests de scripts/sources_panier.mjs : chaque scénario tourne dans un processus enfant (voir aide_releve.mjs).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { lancer, installer, csv, rep, DATE } from './aide_releve.mjs';

const produit = (corps = '<p>Crème</p>', preparer) => ({ html: `<body>${corps}</body>`, preparer });
const paiement = (finale, texte = 'Paiement') => ({ html: `<body>${texte}</body>`, finale });

// tables des requêtes ctx.request : clé « MÉTHODE url »
const REQ = {
  'GET https://c.test/fr/products/c.js': rep({ json: { variants: [{ id: 1, available: false }, { id: 2, available: true }] } }),
  'GET https://c.test/cart.js': rep({ json: { item_count: 1, items: [{ url: '/products/c?variant=2', key: 'k1', quantity: 1, final_line_price: 1250 }], total_price: 1250 } }),
  'GET https://c.test/cart/shipping_rates.json?shipping_address%5Bzip%5D=75001&shipping_address%5Bcountry%5D=France':
    rep({ json: { shipping_rates: [{ name: 'Colissimo', price: '4.90', delivery_range: ['2025-01-02', '2025-01-04'] }, { name: 'Relais', price: '3.90' }] } }),
  'GET https://d.test/products/d.js': rep({ jsonErreur: true }),
  'GET https://d.test/cart.js': rep({ type: 'text/html' }),
  'GET https://e.test/products/e.js': rep({ json: { variants: [{ id: 5, available: false }] } }),
  'GET https://e.test/en/cart.js': rep({ json: { item_count: 2, items: [{ quantity: 1 }, { url: '/x', key: 'k2', quantity: 1 }], total_price: 'x' } }),
  'GET https://e.test/en/cart/shipping_rates.json?shipping_address%5Bzip%5D=75001&shipping_address%5Bcountry%5D=France': rep({ statut: 404 }),
  'POST https://e.test/en/cart/clear.js#2': 'rejet',
  'GET https://f.test/products/f.js': rep({ jsonErreur: true }),
  'GET https://g.test/products/g.js': rep({ jsonErreur: true }),
  'GET https://g.test/cart.js': rep({ statut: 203, type: null }),
  'GET https://h.test/products/h.js': rep({ json: { variants: [{ id: 9, available: true }] } }),
  'GET https://h.test/cart.js': rep({ json: { item_count: 0 } }),
  'GET https://h.test/cart/shipping_rates.json?shipping_address%5Bzip%5D=75001&shipping_address%5Bcountry%5D=France': rep({ jsonErreur: true }),
  'GET https://i.test/products/i.js': rep({ json: { variants: [{ id: 10, available: true }] } }),
  'GET https://i.test/cart.js': rep({ json: { item_count: 1, items: [{ url: '/p', key: 'k', quantity: 0, final_line_price: 100 }], total_price: 100 } }),
  'GET https://i.test/cart/shipping_rates.json?shipping_address%5Bzip%5D=75001&shipping_address%5Bcountry%5D=France': rep({ json: null }),
  'GET https://j.test/products/j.js': rep({ json: { variants: [{ id: 11, available: true }] } }),
  'GET https://j.test/cart.js': rep({ json: { item_count: 1, items: [{ url: '/p', key: 'k', quantity: 1, final_line_price: 100 }], total_price: 100 } }),
  'GET https://j.test/cart/shipping_rates.json?shipping_address%5Bzip%5D=75001&shipping_address%5Bcountry%5D=France': rep({ json: { shipping_rates: [] } }),
  'GET https://l.test/products/l.js': rep({ json: { variants: [{ id: 12, available: true }] } }),
  'GET https://l.test/cart.js': rep({ json: { item_count: 1, items: [{ url: '/p', key: 'k', quantity: 1, final_line_price: 100 }], total_price: 100 } }),
  'GET https://l.test/cart/shipping_rates.json?shipping_address%5Bzip%5D=75001&shipping_address%5Bcountry%5D=France': rep({ json: { shipping_rates: [{ name: 'Standard', price: '5.00' }, { price: '0.00' }] } }),
  'GET https://m.test/products/m.js': rep({ json: { variants: [{ id: 13, available: true }] } }),
  'GET https://m.test/cart.js': rep({ json: { item_count: 1, items: [{ url: '/p', key: 'k', quantity: 1, final_line_price: 100 }], total_price: 100 } }),
  'GET https://m.test/cart/shipping_rates.json?shipping_address%5Bzip%5D=75001&shipping_address%5Bcountry%5D=France': rep({ json: { shipping_rates: [{ name: 'Rapide', price: '9.00', delivery_days: [1, 2] }, { name: 'Lent 2-3 jours', price: '1.00' }] } }),
};
const vus = {};
function requete(m, url) {
  const cle = `${m} ${url}`;
  vus[cle] = (vus[cle] || 0) + 1;
  const r = REQ[`${cle}#${vus[cle]}`] ?? REQ[cle];
  if (r === 'rejet') throw new Error('requête refusée');
  return r ?? rep({ json: {} });
}

export const scenarios = {
  principal: {
    csv: csv([
      ['A', 'Produit', 'https://a.test/products/a'],
      ['B', 'Produit', 'https://b.test/products/b'],
      ['C', 'Accueil', 'https://c.test/'], ['C', 'Produit', 'https://c.test/fr/products/c?variant=1'],
      ['D', 'Produit', 'https://d.test/products/d'], ['E', 'Produit', 'https://e.test/products/e'],
      ['F', 'Produit', 'https://f.test/products/f'], ['G', 'Produit', 'https://g.test/products/g'],
      ['H', 'Produit', 'https://h.test/products/h'], ['I', 'Produit', 'https://i.test/products/i'],
      ['J', 'Produit', 'https://j.test/products/j'], ['K', 'Accueil', 'https://k.test/'],
      ['L', 'Produit', 'https://l.test/products/l'], ['M', 'Produit', 'https://m.test/products/m'],
    ]),
    requete,
    pages: {
      'https://b.test/products/b': produit('Just a moment...'),
      'https://c.test/fr/products/c?variant=1': produit(),
      'https://c.test/fr/checkout': paiement('https://c.test/checkouts/cn/abc', 'Contact Livraison Payer'),
      'https://c.test/cart': produit('Panier'),
      'https://d.test/products/d': produit('', w => { w.Shopify = {}; w.ShopifyAnalytics = { meta: { product: { variants: [{ id: 77 }] } } }; }),
      'https://e.test/products/e': produit('', w => { w.Shopify = { routes: { root: '/en/' } }; }),
      'https://e.test/checkout': { ...paiement('https://e.test/account/login?checkout_url=x'), captureErreur: true },
      'https://e.test/cart': { erreur: 'net::ERR' },
      'https://f.test/products/f': produit('', w => { w.Shopify = { routes: {} }; w.ShopifyAnalytics = { meta: { product: { variants: [] } } }; }),
      'https://g.test/products/g': produit('<form action="/cart/add"><input name="id" value="88"></form>', w => { w.ShopifyAnalytics = { meta: {} }; }),
      'https://h.test/products/h': produit('', w => { w.ShopifyAnalytics = {}; }),
      'https://h.test/checkout': paiement(),
      'https://h.test/cart': produit('Panier'),
      'https://i.test/products/i': produit('', w => { w.ShopifyAnalytics = { meta: { product: {} } }; }),
      'https://i.test/checkout': paiement(),
      'https://i.test/cart': produit('Panier'),
      'https://j.test/products/j': produit(),
      'https://j.test/checkout': paiement('https://shopify.com/authentication/1/login'),
      'https://j.test/cart': produit('Panier'),
      'https://l.test/products/l': produit(),
      'https://l.test/checkout': paiement(),
      'https://l.test/cart': produit('Panier'),
      'https://m.test/products/m': produit(),
      'https://m.test/checkout': paiement(),
      'https://m.test/cart': produit('Panier'),
    },
  },
  sans_deja: { csv: csv([['K', 'Accueil', 'https://k.test/']]), requete, pages: {} },
};

if (process.env.AIDE_NOM) await installer(scenarios[process.env.AIDE_NOM]);
else {
  const panier = `resultats/sources-${DATE()}/panier.json`;
  test('sources_panier : API panier, tarifs, page de paiement et reprise', () => {
    const deja = { A: { 32: ['C', 'déjà', 'x'] }, B: { _non_teste: 'ancien échec' } };
    const r = lancer(import.meta.url, 'sources_panier.mjs', 'principal', {
      args: t => [join(t, 'hors')],
      avant: t => { mkdirSync(join(t, `resultats/sources-${DATE()}`), { recursive: true }); writeFileSync(join(t, panier), JSON.stringify(deja)); },
    });
    try {
      assert.equal(r.statut, 0, r.erreurs);
      const j = r.lire(panier);
      assert.deepEqual(j.A, deja.A);  // repris tel quel
      assert.deepEqual(j.B, { _non_teste: 'vérification anti-robot : non contournée' });
      assert.deepEqual(j.C, {
        32: ['C', 'après un seul ajout, le panier compte 1 article(s) sur 1 ligne(s)', 'API panier Shopify (cart.js)'],
        31: ['C', 'ligne du panier : lien vers la fiche « /products/c »', 'API panier Shopify (cart.js)'],
        38: ['C', 'ligne modifiable par clé (présente), quantité 1', 'API panier Shopify (cart.js)'],
        41: ['C', "prix de ligne 12.50 € et total 12.50 € détaillés par l'API", 'API panier Shopify (cart.js)'],
        36: ['C', '2 tarif(s) de livraison estimé(s) pour Paris, dont « Colissimo » à 4.90 €', 'API panier Shopify (shipping_rates)'],
        35: ['C', 'délai annoncé : « Colissimo » (2025-01-02 à 2025-01-04)', 'API panier Shopify (shipping_rates)'],
        30: ['C', "la page de paiement s'ouvre sans connexion ni création de compte", 'Page de paiement (affichée)'],
      });
      assert.equal(j.D._non_teste, 'cart.js non servi en JSON (code 200)');
      assert.equal(j.E['32'][0], 'NC'); assert.equal(j.E['31'][1], 'ligne du panier : lien vers la fiche « absent »');
      assert.deepEqual(j.E['38'].slice(0, 2), ['NC', 'ligne modifiable par clé (absente), quantité 1']);
      assert.equal(j.E['41'][0], 'NC'); assert.equal(j.E._tarifs, '{"erreur":404}');
      assert.equal(j.E['30'][0], 'NC'); assert.match(j.E['30'][1], /renvoie vers une connexion \(https:\/\/e\.test\/account\/login/);
      assert.equal(j.F._non_teste, 'article introuvable sur la fiche produit');
      assert.equal(j.G._non_teste, 'cart.js non servi en JSON (code 203)');
      assert.deepEqual([j.H['32'][0], j.H['31'][0], j.H['38'][0], j.H['41'][0]], ['NC', 'C', 'NC', 'NC']);
      assert.equal(j.H._tarifs, '{"erreur":"réponse non JSON"}');
      assert.equal(j.I['38'][0], 'NC'); assert.equal(j.I._tarifs, 'null');
      assert.equal(j.J._tarifs, '{"shipping_rates":[]}'); assert.equal(j.J['30'][0], 'NC');
      assert.match(j.K._non_teste, /undefined/);
      assert.deepEqual(j.L['35'], ['NC', 'aucun délai dans les tarifs de livraison', 'API panier Shopify (shipping_rates)']);
      assert.deepEqual(j.M['35'], ['C', 'délai annoncé : « Rapide »', 'API panier Shopify (shipping_rates)']);
      // ajouts : l'article retenu, une seule unité ; panier vidé avant et après
      const posts = r.journal.filter(x => x[0] === 'POST');
      assert.deepEqual(posts.find(x => x[1] === 'https://c.test/cart/add.js')[2], { items: [{ id: 2, quantity: 1 }] });
      assert.deepEqual(posts.find(x => x[1] === 'https://d.test/cart/add.js')[2], { items: [{ id: 77, quantity: 1 }] });
      assert.deepEqual(posts.find(x => x[1] === 'https://e.test/en/cart/add.js')[2], { items: [{ id: 5, quantity: 1 }] });
      assert.deepEqual(posts.find(x => x[1] === 'https://g.test/cart/add.js')[2], { items: [{ id: 88, quantity: 1 }] });
      assert.equal(posts.filter(x => x[1] === 'https://c.test/cart/clear.js').length, 2);
      assert.ok(r.journal.some(x => x[0] === 'goto' && x[1] === 'https://c.test/fr/checkout'));
      assert.equal(r.texte('hors/paiement/C.txt'), 'Contact Livraison Payer');
      assert.ok(r.journal.some(x => x[0] === 'capture' && x[1].endsWith('hors/paiement/C__panier.jpg')));
      assert.ok(!r.journal.some(x => x[0] === 'goto' && x[1].startsWith('https://a.test')));
      assert.match(r.sortie, /^C 30:C 31:C 32:C 35:C 36:C 38:C 41:C $/m);
      assert.match(r.sortie, /^E 30:NC 31:NC 32:NC 38:NC 41:NC \{"erreur":404\}$/m);
      assert.match(r.sortie, /^B vérification anti-robot : non contournée $/m);
      assert.ok(r.sortie.trim().endsWith(`resultats/sources-${DATE()}/panier.json`));
    } finally { r.nettoyer(); }
  });

  test('sources_panier : sans résultat du jour, le fichier est créé', () => {
    const r = lancer(import.meta.url, 'sources_panier.mjs', 'sans_deja', { args: t => [join(t, 'hors')] });
    try {
      assert.equal(r.statut, 0, r.erreurs);
      assert.deepEqual(Object.keys(r.lire(panier)), ['K']);
      assert.ok(r.existe('hors/paiement'));
    } finally { r.nettoyer(); }
  });
}
