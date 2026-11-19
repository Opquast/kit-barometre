// Tests de scripts/parcours.mjs : Playwright simulé (pages jsdom, fetch du panier simulé), sorties et captures
// dans un dossier temporaire.
import { test, mock } from 'node:test';
import assert from 'node:assert/strict';
import { join } from 'node:path';
import { lancer, executerScenario, aujourdhui } from './aide_parcours.mjs';

const CSV = `service,gabarit,url
Boutique A,Accueil,https://a.fr/
Boutique A,Produit,https://a.fr/products/a
Boutique B,Accueil,https://b.fr/
Boutique B,Produit,https://b.fr/products/b
Boutique C,Accueil,https://c.fr/
Boutique C,Produit,https://c.fr/products/c
Boutique D,Accueil,https://d.fr/
Boutique D,Produit,https://d.fr/products/d
Boutique E,Accueil,https://e.fr/
Boutique E,Produit,https://e.fr/products/e
Boutique A2,Accueil,https://a2.fr/
Boutique A2,Produit,https://a2.fr/products/x?variant=1,2`;

const st = o => `data-style='${JSON.stringify(o)}'`;
const json = v => ({ ok: true, json: async () => v });
const PAGES = {
  'https://a.fr/': {
    html: `<body><main>
      <a id="e0" href="#" ${st({ outlineStyle: 'solid', outlineWidth: '2px' })}>Aller au contenu</a>
      <button id="e1" aria-label="Panier" ${st({ boxShadow: '0 0 2px blue' })}></button>
      <input id="e2" value="abc" data-rect="0,0,0,20"><span id="e3" tabindex="0" data-rect="0,0,100,0"></span>
      <a id="e5" href="#" data-rect="0,-50,100,20">Bas</a><a id="e6" href="#" data-rect="0,5000,100,20">Loin</a>
      <a id="e7" href="#">Sans</a><a id="e8" href="#" ${st({ outlineStyle: 'solid', outlineWidth: '0px' })}>Zéro</a>
      </main><footer><form><input type="email" required></form></footer></body>`,
    focus: ['a#e0', 'button#e1', 'input#e2', 'span#e3', 'body', 'a#e5', 'a#e6', 'a#e7', 'a#e8'],
  },
  'https://a.fr/products/a': {
    html: `<body><a id="acc" href="/">Accueil</a><input id="q" name="q" value="Rechercher"><button id="menu" aria-label="Menu"></button>
      <span id="vide" tabindex="0"></span><form action="/cart/add"><select id="qty" name="qty"></select><button id="ajout" type="submit">Ajouter</button></form></body>`,
    focus: [null, 'a#acc', 'input#q', 'button#menu', 'span#vide', 'select#qty', 'button#ajout'],
  },
  'https://a.fr/checkout': {
    finale: 'https://a.fr/12345678901234567890123/checkouts/cn/hWN4abc/fr',
    html: `<html><head><title>Paiement - A</title></head><body><input type="email" name="email">
      <p>Paiement express Shop Pay. Visa, American Express et Amex acceptés. Vous avez un compte ? Se connecter</p>
      <img alt="Mastercard"><svg aria-label="PayPal"></svg><span aria-label=""></span>
      <nav aria-label="Fil"><ol><li>Panier</li><li> </li><li>Paiement</li></ol></nav>
      <label for="c1">Recevoir les offres</label><input type="checkbox" id="c1" checked>
      <input type="checkbox" checked aria-label="Mémoriser"><input type="checkbox" checked name="cgv"><input type="checkbox" checked>
      <label><input type="checkbox" checked></label><input type="checkbox" checked id="c6"><input type="checkbox"></body></html>`,
    preparer: w => Object.defineProperty(w.document.getElementById('c6'), 'labels', { value: null }),
  },
  'https://b.fr/': { html: '<body><div data-cache><input type="email"></div></body>', focus: [null] },
  'https://b.fr/products/b': { finale: 'https://b.fr/products/b/', html: '<body><form action="/cart/add"><button id="add" type="button" name="add">+</button></form></body>', focus: ['button#add'] },
  'https://c.fr/products/c': { focus: [null] },
  'https://d.fr/': { html: '<body><form novalidate><input type="email" aria-invalid="false"></form></body>' },
  'https://d.fr/products/d': { html: '<body><button id="atc">Add to cart</button></body>', focus: ['button#atc'] },
  'https://d.fr/checkout': { html: '<body><p>Connectez-vous pour continuer. Vérifiez que vous êtes humain.</p></body>' },
  'https://e.fr/': { erreur: 'net::ERR_CONNECTION_REFUSED\nCall log' },
  'https://a2.fr/products/x?variant=1,2': { html: '<body><button id="atc">Ajouter au panier</button></body>', focus: ['button#atc'] },
};

const FETCH = {
  'a.fr': { '/cart.js': json({ item_count: 1 }) },
  'b.fr': { '/cart.js': json({ item_count: 0 }), '/products/b.js': json({ variants: [{ id: 1, available: false }, { id: 2, available: false }] }), '/cart/add.js': { ok: false } },
  'd.fr': { '/products/d.js': json({ variants: [{ id: 5, available: false }, { id: 6, available: true }] }), '/cart/add.js': { ok: true } },
  'a2.fr': { '/cart.js': json({ item_count: 2 }) },
};

const SITE = {
  page: url => PAGES[url] ?? {},
  touche: (k, page) => (k === 'Escape' && page.url() === 'https://b.fr/' ? Promise.reject(new Error('page fermée')) : undefined),
  visible: (d, page) => {
    const u = page.url();
    if (u === 'https://b.fr/') return d.sel === '#onetrust-reject-all-handler' ? Promise.reject(new Error('détaché')) : d.sel === 'button:has-text("Refuser")';
    return u === 'https://d.fr/' && d.sel === '#onetrust-reject-all-handler';
  },
  clic: (d, page) => (page.url() === 'https://b.fr/' ? Promise.reject(new Error('masqué')) : undefined),
  capture: o => (/_focus_2|Boutique_A_paiement/.test(o.path) ? Promise.reject(new Error('capture impossible')) : undefined),
  fetch: async (u, o, page) => {
    const r = FETCH[new URL(page.url()).host]?.[u];
    if (!r) throw new Error(`fetch refusé : ${u}`);
    return r;
  },
};

const SCENARIOS = {
  complet: tmp => ({ csv: CSV, args: ['--captures', join(tmp, 'captures')], site: SITE }),
  service: () => ({ csv: CSV, args: ['--service', 'Boutique A2'], site: SITE }),
};

if (process.env.AIDE_SCENARIO) {
  await executerScenario(mock, 'parcours.mjs', SCENARIOS[process.env.AIDE_SCENARIO](process.env.AIDE_TMP));
} else {
  const fichier = `resultats/parcours-${aujourdhui()}/parcours.json`;

  test('parcours : clavier, formulaire newsletter, ajout au panier et page de paiement, avec captures', () => {
    const r = lancer(import.meta.url, 'complet');
    assert.equal(r.status, 0, r.stderr);
    assert.ok(r.existe('captures'), 'dossier des captures créé');
    const p = JSON.parse(r.lire(fichier));
    assert.deepEqual(Object.keys(p), ['Boutique A', 'Boutique B', 'Boutique C', 'Boutique D', 'Boutique E', 'Boutique A2']);

    const a = p['Boutique A'];
    assert.deepEqual(a.clavier_accueil, { tabulations: 25, elements_atteints: 22, invisibles: 12, sans_indicateur: 4,
      premiers: ['a « Aller au contenu »', 'button « Panier »', 'input « abc »', 'span «  »', 'a « Bas »', 'a « Loin »', 'a « Sans »', 'a « Zéro »'] });
    assert.deepEqual(a.formulaire, { trouve: true, valide: false, message_navigateur: 'Constraints not satisfied', type: 'email', requis: true,
      message_propre_au_site: false, aria_invalid: null });
    assert.deepEqual(a.clavier_produit, { bouton_panier_atteint_en_tabulations: 7, ajout_au_clavier: true });
    assert.deepEqual(a.paiement, { champ_email_ou_tel: true, connexion_obligatoire: false, lien_connexion_facultatif: true,
      moyens_paiement: ['Visa', 'Mastercard', 'Amex', 'PayPal', 'Shop Pay'], paiement_express: true, etapes: ['Panier', 'Paiement'],
      titre: 'Paiement - A', cases_precochees: ['Recevoir les offres', 'Mémoriser', 'cgv', '', '', ''], verification_humaine: false,
      url: 'a.fr/…/checkouts/cn/…/fr' });

    const b = p['Boutique B'];
    assert.equal(b.clavier_accueil.elements_atteints, 0);
    assert.deepEqual(b.formulaire, { trouve: true, valide: false, message_navigateur: 'Constraints not satisfied', type: 'email', requis: false,
      message_propre_au_site: false, aria_invalid: null });
    assert.deepEqual(b.clavier_produit, { bouton_panier_atteint_en_tabulations: 1, ajout_au_clavier: false });
    assert.deepEqual(b.paiement, { non_teste: 'ajout au panier impossible' });

    const c = p['Boutique C'];
    assert.deepEqual(c.formulaire, { trouve: false });
    assert.deepEqual(c.clavier_produit, { bouton_panier_atteint_en_tabulations: null, ajout_au_clavier: false });
    assert.deepEqual(c.paiement, { non_teste: 'ajout au panier impossible' });

    const d = p['Boutique D'];
    assert.equal(d.formulaire.message_propre_au_site, true);
    assert.equal(d.formulaire.aria_invalid, 'false');
    assert.deepEqual(d.clavier_produit, { bouton_panier_atteint_en_tabulations: 1, ajout_au_clavier: false });
    assert.deepEqual(d.paiement, { champ_email_ou_tel: false, connexion_obligatoire: true, lien_connexion_facultatif: false, moyens_paiement: [],
      paiement_express: false, etapes: [], titre: '', cases_precochees: [], verification_humaine: true, url: 'd.fr/checkout' });

    assert.deepEqual(p['Boutique E'], { erreur: 'net::ERR_CONNECTION_REFUSED' });

    // ajout de secours : première variante si aucune n'est disponible, sinon la première disponible
    const posts = r.journal.filter(x => x[0] === 'fetch' && x[1] === '/cart/add.js').map(x => JSON.parse(x[2]).items[0].id);
    assert.deepEqual(posts, [1, 6]);
    assert.equal(r.journal.filter(x => x[0] === 'fetch' && x[1] === '/products/b.js').length, 1, 'barre oblique finale retirée');
    // C : 400 tabulations sans trouver le bouton
    const iC = r.journal.findIndex(x => x[0] === 'goto' && x[1] === 'https://c.fr/products/c');
    const iD = r.journal.findIndex(x => x[0] === 'goto' && x[1] === 'https://d.fr/');
    assert.equal(r.journal.slice(iC, iD).filter(x => x[0] === 'touche' && x[1] === 'Tab').length, 400);
    // captures : seulement les éléments visibles parmi les 6 premiers, puis la page de paiement
    const captures = r.journal.filter(x => x[0] === 'capture').map(x => x[1].replace(join(r.tmp, 'captures'), ''));
    assert.deepEqual(captures, ['/Boutique_A_focus_1.png', '/Boutique_A_focus_2.png', '/Boutique_A_paiement.png', '/Boutique_D_paiement.png', '/Boutique_A2_paiement.png']);
    assert.deepEqual(r.journal.find(x => x[0] === 'capture')[2], { x: 0, y: 0, width: 116, height: 36 });
    // un contexte jetable par site, refermé même après une erreur
    assert.equal(r.journal.filter(x => x[0] === 'closeContext').length, 6);
    assert.equal(r.journal.at(-1)[0], 'close');
  });

  test('parcours : --service sans dossier de captures', () => {
    const r = lancer(import.meta.url, 'service');
    assert.equal(r.status, 0, r.stderr);
    const p = JSON.parse(r.lire(fichier));
    assert.deepEqual(Object.keys(p), ['Boutique A2']);
    assert.deepEqual(p['Boutique A2'].clavier_produit, { bouton_panier_atteint_en_tabulations: 1, ajout_au_clavier: true });
    assert.equal(p['Boutique A2'].paiement.url, 'a2.fr/checkout');
    assert.equal(r.journal.filter(x => x[0] === 'capture').length, 0);
    assert.ok(!r.existe('captures'));
  });
}
