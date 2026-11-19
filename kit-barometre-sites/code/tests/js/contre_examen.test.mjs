// Tests de scripts/contre_examen.mjs : Playwright simulé (pages jsdom), sortie dans un dossier temporaire.
import { test, mock } from 'node:test';
import assert from 'node:assert/strict';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { lancer, executerScenario, aujourdhui } from './aide_parcours.mjs';

const CSV = `service,gabarit,url
Boutique A,Accueil,https://a.fr/
Boutique A,Produit,https://a.fr/products/p
Boutique A,Page CGV,https://a.fr/pages/cgv
Boutique A,Page FAQ,https://a.fr/pages/faq
Boutique D,Accueil FR,https://d.fr/fr
Boutique D,Collection,https://d.fr/collections/x
Boutique D,Page 1,https://d.fr/pages/1
Boutique D,Page 2,https://d.fr/pages/2
Boutique E,Accueil,https://e.fr/
Boutique E,Produit,https://e.fr/products/e
Boutique E,Page,https://e.fr/pages/e
Boutique F,Accueil,https://f.fr/
Boutique H,Accueil,https://h.fr/
Boutique H,Produit,https://h.fr/products/h
Boutique G,Accueil,https://g.fr/
Boutique G,Produit,https://g.fr/products/g`;

const st = o => `data-style='${JSON.stringify(o)}'`;
const PAGES = {
  'https://a.fr/': {
    html: `<body><header>Accueil</header><main><p>Livraison <abbr title="Union européenne">UE</abbr> et SAV offert. Paiement CB TTC FR.</p>
      <a id="l1" href="#" aria-label="Aller au contenu principal du site web" ${st({ outlineStyle: 'solid', outlineWidth: '2px' })}>x</a>
      <button id="b2" ${st({ outlineStyle: 'solid', outlineWidth: '0px', boxShadow: '' })}>b</button>
      <a id="l3" href="#" ${st({ boxShadow: '0 0 0 2px red' })}>y</a><a id="l4" href="#">z</a></main>
      <footer><span>Visa</span><span>Mastercard</span><img alt="PayPal"><i class="apple_pay"></i></footer></body>`,
    focus: ['a#l1', 'button#b2', 'body', 'a#l3', null, 'a#l4'],
  },
  'https://a.fr/products/p': { html: '<body><p>Coton bio. Fabriqué en France.</p></body>' },
  'https://a.fr/pages/cgv': {
    html: `<body><main>
      <p>Texte <a href="#" ${st({ textDecorationLine: 'underline' })}>souligné</a> et <a href="#">  Lien nu  </a> et <a href="#" ${st({ fontWeight: '700' })}>gras</a></p>
      <p data-cache><a href="#">caché</a></p><ul><li><a href="#">liste</a></li></ul>
      <div class="rte"><span><a href="#">rte</a></span></div></main></body>`,
  },
  'https://a.fr/pages/faq': { status: 404 },
  'https://a.fr/account/register': {
    html: `<body><form><input type="email"></form>
      <form><input type="password"><input type="password"><button>Créer</button><button type="button" aria-label="Afficher le mot de passe"></button><p>Robustesse : faible</p></form>
      <a href="#">Continuer avec Google</a><button aria-label="Apple">x</button><a href="#">Aide</a></body>`,
  },
  'https://a.fr/page-qui-nexiste-pas-barometre': { status: 404, html: '<body><header></header><main>  Oups, page introuvable  </main><footer></footer></body>' },
  'https://d.fr/fr': { html: '<body><main><p>bienvenue chez nous</p></main></body>', focus: [null] },
  'https://d.fr/pages/1': { status: null },
  'https://d.fr/pages/2': { finale: 'https://autre.fr/p' },
  'https://d.fr/fr/account/register': { status: null, finale: 'https://shopify.com/authentication/12345678/login' },
  'https://d.fr/page-qui-nexiste-pas-barometre': { status: null, html: '<body><div>rien</div></body>' },
  'https://e.fr/products/e': { html: '<body><p>Coton bio.</p></body>' },
  'https://e.fr/pages/e': { html: '<body><article><p><a href="#"></a></p></article></body>' },
  'https://e.fr/page-qui-nexiste-pas-barometre': { status: 404, html: '<body><main></main></body>' },
  'https://f.fr/': { erreur: 'net::ERR_NAME_NOT_RESOLVED at https://f.fr/\nCall log' },
  'https://h.fr/products/h': { status: 500 },
  'https://g.fr/products/g': { status: null },
};

const SITE = {
  page: url => PAGES[url] ?? {},
  visible: (d, page) => {
    if (page.url() === 'https://a.fr/') return true;
    if (page.url() === 'https://e.fr/' && /refuser/.test(d.name.source)) return Promise.reject(new Error('détaché'));
    return false;
  },
  clic: d => (/fermer/.test(d.name.source) ? Promise.reject(new Error('masqué')) : undefined),
};

// parc de test (referentiel/parc.json remplacé par BAROMETRE_PARC) : seule Boutique D est auditée sous /fr
function parcDeTest() {
  const f = join(process.env.AIDE_TMP, 'parc.json');
  writeFileSync(f, JSON.stringify({ responsable: 'Mattea', sites: [{ nom: 'Boutique D', prefixe_langue: '/fr' }, { nom: 'Boutique A', prefixe_langue: '' }] }));
  process.env.BAROMETRE_PARC = f;
}

const SCENARIOS = {
  complet: () => { parcDeTest(); return { csv: CSV, args: [], site: SITE }; },
  service: () => { parcDeTest(); return { csv: CSV, args: ['--service', 'Boutique G'], site: SITE }; },
};

if (process.env.AIDE_SCENARIO) {
  await executerScenario(mock, 'contre_examen.mjs', SCENARIOS[process.env.AIDE_SCENARIO]());
} else {
  const fichier = `resultats/contre-examen-${aujourdhui()}/constats.json`;

  test('contre_examen : constats de chaque règle sur six boutiques aux cas variés', () => {
    const r = lancer(import.meta.url, 'complet');
    assert.equal(r.status, 0, r.stderr);
    const c = JSON.parse(r.lire(fichier));
    assert.equal(c.date, aujourdhui());
    assert.equal(c.outil, 'scripts/contre_examen.mjs (Playwright, Chromium)');
    assert.deepEqual(Object.keys(c.sites), ['Boutique A', 'Boutique D', 'Boutique E', 'Boutique F', 'Boutique H', 'Boutique G']);

    const a = c.sites['Boutique A'];
    assert.deepEqual(a.r5, { abbr_title: 1, sigles_dans_le_texte: ['UE', 'SAV', 'CB'] });
    assert.deepEqual(a.r58, { moyens_de_paiement: ['visa', 'mastercard', 'paypal', 'apple pay'] });
    assert.deepEqual(a.r165, { elements_atteints: 10, sans_focus_visible: 5, exemples_sans_focus: ['button', 'a', 'button', 'a'] });
    assert.deepEqual(a.r166, { elements_atteints_au_clavier_sur_15_tabs: 10, premier: `a[${'Aller au contenu principal du site web'.slice(0, 30)}]` });
    assert.equal(a.r216.conforme, true);
    assert.deepEqual(a.r68, { mention_trouvee: true, extrait: 'Coton bio. Fabriqué en France.' });
    assert.deepEqual(a.r140.pages, [
      { page: 'Page CGV', liens_dans_le_texte: 4, sans_soulignement_ni_graisse: 2, exemple: 'Lien nu' },
      { page: 'Page FAQ', non_teste: true },
    ]);
    assert.deepEqual(a.inscription, { formulaire: true, champs_mot_de_passe: 2, boutons_identification_tierce: 2,
      bouton_afficher_mot_de_passe: true, jauge_robustesse: true, url: 'a.fr/account/register', code: 200 });
    assert.deepEqual(a.r223, { code: 404, en_tete_du_site: true, pied_du_site: true, texte: 'Oups, page introuvable' });

    const d = c.sites['Boutique D'];
    assert.deepEqual(d.r5, { abbr_title: 0, sigles_dans_le_texte: [] });
    assert.deepEqual(d.r58, { moyens_de_paiement: [] });
    assert.deepEqual(d.r165, { elements_atteints: 0, sans_focus_visible: 0, exemples_sans_focus: [] });
    assert.equal(d.r166.premier, '');
    assert.equal(d.r68, undefined, 'pas de fiche produit dans l\'échantillon');
    assert.deepEqual(d.r140.pages, [{ page: 'Page 1', non_teste: true }, { page: 'Page 2', non_teste: true }]);
    assert.deepEqual(d.inscription, { hors_site: 'shopify.com', constat: 'Comptes clients hébergés par Shopify (connexion par code envoyé par e-mail, sans mot de passe).',
      url: 'shopify.com/authentication/[id]/login', code: null });
    assert.deepEqual(d.r223, { code: null, en_tete_du_site: false, pied_du_site: false, texte: '' });

    const e = c.sites['Boutique E'];
    assert.deepEqual(e.r68, { mention_trouvee: false, extrait: '' });
    assert.deepEqual(e.r140.pages, [
      { page: 'Produit', liens_dans_le_texte: 0, sans_soulignement_ni_graisse: 0, exemple: '' },
      { page: 'Page', liens_dans_le_texte: 1, sans_soulignement_ni_graisse: 1, exemple: '' },
    ]);
    assert.deepEqual(e.inscription, { formulaire: false, url: 'e.fr/account/register', code: 200 });
    assert.deepEqual(e.r223, { code: 404, en_tete_du_site: false, pied_du_site: false, texte: '' });

    assert.deepEqual(c.sites['Boutique F'], { erreur: 'net::ERR_NAME_NOT_RESOLVED at https://f.fr/' });
    const h = c.sites['Boutique H'];
    assert.deepEqual(h.r68, { non_teste: 'code 500' });
    assert.deepEqual(h.r140.pages[1], { page: 'Produit', non_teste: true });

    // bandeau : refus cliqué puis fermeture tentée (son échec n'arrête rien), jamais d'acceptation
    const clics = r.journal.filter(x => x[0] === 'clic').map(x => x[2]);
    assert.ok(clics.length >= 2 && clics.every(x => /refuser|fermer/.test(x)));
    assert.equal(r.journal.filter(x => x[0] === 'touche' && x[1] !== 'Tab').length, 0);
    assert.equal(r.journal.at(-1)[0], 'close');
    assert.match(r.stdout, /constats\.json/);
  });

  test('contre_examen : --service ; fiche produit sans réponse', () => {
    const r = lancer(import.meta.url, 'service');
    assert.equal(r.status, 0, r.stderr);
    const c = JSON.parse(r.lire(fichier));
    assert.deepEqual(Object.keys(c.sites), ['Boutique G']);
    assert.deepEqual(c.sites['Boutique G'].r68, { non_teste: 'code ?' });
  });
}
