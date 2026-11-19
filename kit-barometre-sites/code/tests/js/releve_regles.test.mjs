// Tests de scripts/releve_regles.mjs : chaque scénario tourne dans un processus enfant (voir aide_releve.mjs).
// Les fonctions passées à page.evaluate (MESURES, popups, panier…) s'exécutent pour de vrai dans un DOM jsdom ;
// styles calculés et boîtes viennent des attributs style / data-style-print / data-r des pages simulées.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, writeFileSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { lancer, installer, csv, rep, DATE } from './aide_releve.mjs';

const FIXE = z => `position: fixed; z-index: ${z}`;
// éléments qui échouent chacun à une condition différente du repérage des popups
const LEURRES = `
<div style="z-index: 500" data-r="0 0 600 400">statique</div>
<div style="position: absolute; z-index: 50" data-r="0 0 600 400">z faible</div>
<div style="${FIXE(500)}" data-r="0 0 200 400">étroit</div>
<div style="${FIXE(500)}" data-r="0 0 600 100">bas</div>
<div style="${FIXE(500)}; display: none" data-r="0 0 600 400">masqué</div>
<div style="${FIXE(500)}; visibility: hidden" data-r="0 0 600 400">invisible</div>
<div style="${FIXE(500)}; opacity: 0" data-r="0 0 600 400">transparent</div>`;

const opts = (attr, l) => `<select ${attr}>${l.map(o => `<option>${o}</option>`).join('')}</select>`;

const ACCUEIL_A = `<head><title>A</title>
<style>a:visited{color:purple} .promo::before{content:"Nouveau !"} .ico::after{content:"x"} @media print{a{color:#000}}</style>
<meta property="article:published_time" content="2025-01-01">
<link rel="alternate" hreflang="en" href="https://a.test/en">
<script type="application/ld+json">{"datePublished":"2025-01-01"}</script></head>
<body>
<header data-r="0 0 1000 80" data-style-print="display: none"><nav data-r="0 0 1000 40" data-style-print="visibility: hidden"><a href="/">Accueil</a><a href="/collections/nouveautes">NOUVEAUTÉS</a></nav></header>
<main>
<h1>BIENVENUE chez nous</h1><h2 style="text-transform: uppercase">PROMOTIONS du jour</h2><h3>SALE</h3><button>ok</button>
<p style="text-decoration-line: underline" data-r="0 0 100 20">Texte souligné un</p>
<p style="text-decoration-line: underline" data-r="0 0 100 20">Texte souligné deux</p>
<p style="text-decoration-line: underline; display: none" data-r="0 0 100 20">caché</p>
<p style="text-decoration-line: underline">largeur nulle</p>
<span style="text-decoration-line: underline">ab</span><div></div>
<span>★★★★☆ avis</span><span aria-label="5 étoiles">★</span><span aria-hidden="true">✓</span><span style="display: none">→</span>
<a href="https://autre.test/x" aria-label="Partenaire (nouvelle fenêtre)">Partenaire</a>
<a href="https://www.autre2.test/" title="lien externe">B</a>
<a href="https://autre3.test/"><svg class="icon-external"></svg>C</a>
<a href="https://autre4.test/">D</a>
<a href="https://www.a.test/page">même site</a><a href="https://cdn.shopify.com/x">s</a><a href="https://shop.app/y">s</a><a href="http://[">cassé</a>
<a href="mailto:contact@a.test">contact@a.test</a><a href="mailto:x@a.test">Écrire</a><a href="mailto:y@a.test">ici</a>
<select name="pays"><optgroup label="E">${['Allemagne', 'Belgique', 'Espagne', 'France', 'Italie', 'Suisse'].map(o => `<option>${o}</option>`).join('')}</optgroup></select>
${opts('id="taille"', ['1 an', '2 ans', '3 ans', '4 ans', '5 ans', '10 ans'])}
${opts('', ['Zèbre', 'Ane', 'Chat', 'Bœuf', 'Dinde', 'Ours'])}
${opts('name="court"', ['a', 'b'])}
<label for="nom">Nom (50 caractères max)</label><input id="nom" name="nom" maxlength="50">
<input name="cp" maxlength="5" aria-describedby="aide-cp"><span id="aide-cp">5 chiffres</span>
<input name="tel" maxlength="10" aria-describedby="absent">
<input name="code" maxlength="8" placeholder="8 car.">
<input name="long" maxlength="500"><input type="hidden" name="h" maxlength="5"><textarea name="msg" maxlength="150"></textarea>
<time datetime="2025-02-03">3 février</time><p>Publié le 12/03/2024 et le 1er janvier 2025</p>
<div class="slideshow" data-autoplay="true"></div><marquee>défile</marquee><button aria-label="Pause">||</button>
<p>Voir ci-dessous les offres. Cliquez sur le bouton rouge pour valider.</p><p>----- =====</p>
<table role="presentation"><tr><th>a</th></tr><tr><td>b</td></tr></table>
<p>- un
- deux
- trois</p><div>- un seul</div>
<img alt="Grande promotion sur toute la gamme de soins" data-nw="800"><img alt="petit texte" data-nw="900"><img alt="un deux trois quatre cinq six sept" data-nw="100">
<a href="/en" hreflang="en">English</a><a href="/de" hreflang="de">Deutsch</a><a href="/en2" hreflang="en">EN</a>
<div class="language-picker"><a lang="es">Español</a></div>
</main>
<div id="onetrust-banner" style="${FIXE(1000)}" data-r="0 600 1366 300">Nous utilisons des cookies pour la mesure d'audience</div>
<div class="popup" style="${FIXE(999)}" data-r="400 200 500 300"><form><input type="email"></form>Newsletter : 1 e-mail par semaine<button aria-label="Fermer" data-r="860 210 30 30">×</button></div>
${LEURRES}
<footer data-r="0 2000 1000 300">© 2025 A, contact@a.test, 01 23 45 67 89
<a href="/pages/mentions-legales">Mentions légales</a><a href="/pages/cgv#haut">CGV</a><a href="/pages/cgv">Conditions générales</a><a href="/policies/">Confidentialité</a>
<a href="/pages/faq">FAQ</a><a href="/pages/contact">Contact</a><a href="https://autre.test/contact">Contact externe</a><a href="/collections/all">Produits</a></footer>
</body>`;

const ACCUEIL_B = `<body><p>Nos nouveautés. Tous droits réservés</p>
<div style="position: absolute; z-index: 200" data-r="0 0 600 400">Code -10 % offert <a data-r="900 900 10 10">Non merci</a></div>
<a href="/pages/livraison">Livraison</a></body>`;

const PRODUIT_A = `<body><header data-r="0 0 1000 80" data-style-print="display: none"><nav data-r="0 0 100 40"><a href="/">Accueil</a></nav></header>
<main>Crème 12,90 € TTC. Contenance 50 ml. En stock. Livraison sous 3 jours. Livraison offerte dès 50 €. -20 % jusqu'au 31 mars. Payez en 3 fois. garantie 2 ans.
<img alt="Label bio Ecocert"><img alt="photo"><video controls data-duree="31.6"></video><video></video>
<select><option disabled>50 ml - épuisé</option><option>100 ml</option></select><svg class="sold-out"></svg><span class="disabled">Indisponible</span></main></body>`;

const PANIER_A = `<body><main><a href="/products/p">Crème</a><input name="updates[]" type="number"><a href="/cart/change?line=1&amp;quantity=0">Supprimer</a>
Sous-total 25,80 € TTC. Livraison sous 48 h.</main></body>`;

// feuilles de style illisibles (origine tierce), sans règles, et règles sans déclaration
const FEUILLES = w => {
  const vraies = w.document.styleSheets;
  const tierce = { get cssRules() { throw new Error('SecurityError'); } };
  Object.defineProperty(w.document, 'styleSheets', { get: () => [...vraies, tierce, { cssRules: null }, { cssRules: [{ selectorText: '.y::after', style: null }, { selectorText: '.z::before', style: {} }] }] });
};
const RACINE_FR = w => { w.Shopify = { routes: { root: '/fr/' } }; };

export const scenarios = {
  principal: {
    csv: csv([
      ['A', 'Accueil', 'https://a.test/'], ['A', 'Produit', 'https://a.test/products/p'], ['A', 'Collection', 'https://a.test/collections/all'],
      ['A', 'Blog', 'https://a.test/blogs/news'], ['A', 'Panier', 'https://a.test/cart'], ['A', 'Compte', 'https://a.test/account'],
      ['B', 'Accueil', 'https://b.test/'], ['B', 'Produit', 'https://b.test/products/q'],
      ['C', 'Accueil', 'https://c.test/'], ['C', 'Produit', 'https://c.test/products/c'],
      ['D', 'Accueil', 'https://d.test/'], ['D', 'Produit', 'https://d.test/products/d'],
      ['F', 'Accueil', 'https://f.test/'], ['F', 'Produit', 'https://f.test/products/f'],
    ]),
    pages: {
      'https://a.test/': { html: ACCUEIL_A, preparer: FEUILLES, visibles: { '#onetrust-reject-all-handler': 'erreur', 'button:has-text("Tout refuser")': true } },
      'https://a.test/pages/mentions-legales': { html: '<body><main>Éditeur :   SAS A\tParis</main></body>' },
      'https://a.test/pages/cgv': { html: '<body>Conditions générales de vente</body>', statut: 200 },
      'https://a.test/policies/': { html: '<body><main>Politique</main></body>' },
      'https://a.test/pages/faq': { erreur: 'net::ERR_TIMED_OUT' },
      'https://a.test/pages/contact': { html: '<body><main>Contact</main></body>', statut: null },
      'https://a.test/page-qui-n-existe-pas-opquast': { html: '<body><header><nav role="navigation"><a href="/">x</a></nav><a href="/c">c</a></header></body>', statut: 404 },
      'https://a.test/products/p': {
        html: PRODUIT_A, visibles: { '#onetrust-reject-all-handler': 'clic-erreur' }, preparer: RACINE_FR,
        fetch: {
          'https://a.test/products/p.js': rep({ json: { variants: [{ id: 1, available: false }, { id: 2, available: true }] } }),
          'https://a.test/fr/cart/add.js': rep(),
        },
      },
      'https://a.test/cart': { html: PANIER_A, preparer: RACINE_FR, fetch: { 'https://a.test/fr/cart.js': rep({ json: { item_count: 2, items: [{ id: 2 }, { id: 9 }] } }) } },
      'https://a.test/collections/all': { html: '<body><p>Collection</p></body>' },
      'https://a.test/blogs/news': { erreur: 'net::ERR_ABORTED' },
      'https://b.test/': { html: ACCUEIL_B },
      'https://b.test/pages/livraison': { html: '<body>Livraison</body>' },
      'https://b.test/page-qui-n-existe-pas-opquast': { statut: null },
      'https://b.test/products/q': {
        html: '<body><nav>menu</nav><p>Rien</p></body>', preparer: w => { w.Shopify = {}; },
        fetch: { 'https://b.test/products/q.js': rep({ json: { variants: [{ id: 3, available: false }] } }), 'https://b.test/cart/add.js': rep() },
      },
      'https://b.test/cart': { html: '<body>Panier</body>' },
      'https://d.test/': { erreur: 'page.goto: net::ERR_NAME_NOT_RESOLVED\nCall log: …' },
      'https://f.test/': { html: '<body><header>x</header></body>' },
      'https://f.test/page-qui-n-existe-pas-opquast': { html: '<body></body>', statut: 404 },
      'https://f.test/products/f': { erreur: 'boom' },
    },
  },
  seul: {
    csv: csv([['A', 'Accueil', 'https://a.test/'], ['A', 'Produit', 'https://a.test/products/p'], ['E', 'Accueil', 'https://e.test/'], ['E', 'Produit', 'https://e.test/products/e']]),
    pages: {
      'https://e.test/': { html: `<body><header class="header">x</header><div style="${FIXE(300)}" data-r="0 0 400 300"><form></form>Inscription</div></body>` },
      'https://e.test/page-qui-n-existe-pas-opquast': { html: '<body></body>' },
      'https://e.test/products/e': {
        html: '<body><p>Produit</p></body>', preparer: w => { w.Shopify = { routes: {} }; },
        fetch: { 'https://e.test/products/e.js': rep({ jsonErreur: true }) },
      },
    },
  },
};

if (process.env.AIDE_NOM) await installer(scenarios[process.env.AIDE_NOM]);
else {
  const sortie = `resultats/releve-${DATE()}/releve.json`;
  test('releve_regles : relevé complet, reprise et erreurs', () => {
    const deja = { C: { fini: true, gardé: 1 }, D: { pages: {}, partiel: true } };
    const r = lancer(import.meta.url, 'releve_regles.mjs', 'principal', {
      args: t => [join(t, 'textes')],
      avant: t => { mkdirSync(join(t, `resultats/releve-${DATE()}`), { recursive: true }); writeFileSync(join(t, sortie), JSON.stringify(deja)); },
    });
    try {
      assert.equal(r.statut, 0, r.erreurs);
      const j = r.lire(sortie);
      assert.deepEqual(j.C, deja.C);
      assert.deepEqual(j.D, { pages: {}, legales: {}, erreur: 'page.goto: net::ERR_NAME_NOT_RESOLVED' });
      const a = j.A;
      assert.equal(a.fini, true);
      assert.deepEqual(a.popup, { presente: true, texte: 'Newsletter : 1 e-mail par semaine×', bouton_fermer: true, libelle_fermer: 'Fermer', fermer_dans_la_popup: true, frequence_annoncee: true });
      assert.deepEqual(a.bandeau_cookies, { finalites_expliquees: true });
      assert.ok(a.pied_de_page.startsWith('© 2025 A, [adresse masquée], [téléphone masqué] Mentions légales'));
      assert.ok(!/contact@|01 23/.test(a.pied_de_page));
      assert.deepEqual(a.impression_accueil, { entete_visible: false, nav_visible: false, pied_visible: true });
      const m = a.mesures_accueil;
      assert.equal(m.copyright, true);
      assert.equal(m.liens_externes, 5); assert.equal(m.liens_externes_signales, 4);  // dont le « Contact externe » du pied de page
      assert.deepEqual(m.mailto, [true, true, false]);
      assert.equal(m.soulignes_hors_lien, 2); assert.equal(m.exemple_souligne, 'Texte souligné un');
      assert.equal(m.regles_visited, 1);
      assert.deepEqual(m.contenus_generes_texte, ['.promo::before "Nouveau !"']);
      assert.deepEqual(m.pictos, [{ car: '★', contexte: '★★★★☆ avis', alternative: false }, { car: '★', contexte: '★', alternative: true }]);
      assert.deepEqual(m.caps_en_dur, ['NOUVEAUTÉS', 'BIENVENUE chez nous']);
      assert.deepEqual(m.selects, [
        { nom: 'pays', options: 6, tri_alpha: true, tri_num: false, optgroup: true, exemples: ['Allemagne', 'Belgique', 'Espagne', 'France'] },
        { nom: 'taille', options: 6, tri_alpha: false, tri_num: true, optgroup: false, exemples: ['1 an', '2 ans', '3 ans', '4 ans'] },
        { nom: '', options: 6, tri_alpha: false, tri_num: false, optgroup: false, exemples: ['Zèbre', 'Ane', 'Chat', 'Bœuf'] },
      ]);
      assert.deepEqual(m.maxlength, [
        { nom: 'nom', max: 50, signale: true }, { nom: 'cp', max: 5, signale: true }, { nom: 'tel', max: 10, signale: false },
        { nom: 'code', max: 8, signale: true }, { nom: 'msg', max: 150, signale: false },
      ]);
      assert.deepEqual(m.time_datetime, ['2025-02-03']); assert.equal(m.meta_date, '2025-01-01'); assert.equal(m.ld_date, true);
      assert.deepEqual(m.dates_texte, ['12/03/2024', '1er janvier 2025']);
      assert.equal(m.carrousels_auto, 2); assert.equal(m.bouton_pause, true);
      assert.deepEqual(m.designation_position, ['ci-dessous les offres', 'bouton rouge pour valider']);
      assert.equal(m.ascii_decoratif, 2); assert.equal(m.nouveautes, true);
      assert.deepEqual(m.tableaux, [{ th: 1, lignes: 2, role: 'presentation' }]);
      assert.equal(m.listes_simulees, 1);
      assert.deepEqual(m.images_texte, ['Grande promotion sur toute la gamme de soins']);
      assert.deepEqual(m.langues, ['en', 'de']);
      assert.deepEqual(m.lien_langue_textes, [
        { texte: 'English', lang: 'en', href: '/en' }, { texte: 'Deutsch', lang: 'de', href: '/de' }, { texte: 'EN', lang: 'en', href: '/en2' }, { texte: 'Español', lang: 'es', href: '' },
      ]);
      // pages légales du pied de page : dédoublonnées, sans ancre, même origine ; textes complets hors dépôt
      assert.deepEqual(Object.keys(a.legales), ['https://a.test/pages/mentions-legales', 'https://a.test/pages/cgv', 'https://a.test/policies/', 'https://a.test/pages/faq', 'https://a.test/pages/contact']);
      const ml = a.legales['https://a.test/pages/mentions-legales'];
      assert.deepEqual({ ...ml, fichier: undefined }, { libelle: 'Mentions légales', statut: 200, caracteres: 'Éditeur : SAS A Paris'.length, fichier: undefined });
      assert.equal(readFileSync(ml.fichier, 'utf8'), 'https://a.test/pages/mentions-legales\nMentions légales\n\nÉditeur : SAS A Paris');
      assert.equal(a.legales['https://a.test/pages/cgv'].libelle, 'Conditions générales');
      assert.ok(a.legales['https://a.test/policies/'].fichier.endsWith('/textes/A__index.txt'));
      assert.deepEqual(a.legales['https://a.test/pages/faq'], { libelle: 'FAQ', erreur: 'net::ERR_TIMED_OUT' });
      assert.equal(a.legales['https://a.test/pages/contact'].statut, undefined);
      assert.deepEqual(readdirSync(join(r.tmp, 'textes')).sort(), ['A__cgv.txt', 'A__contact.txt', 'A__index.txt', 'A__mentions_legales.txt', 'B__livraison.txt']);
      assert.deepEqual(a.page_404, { menu: true, liens_entete: 2, code: 404 });
      assert.deepEqual(a.produit, {
        prix: '12,90 €', ttc: true, caracteristiques: true, disponibilite: true, delai_livraison: true, frais_livraison: true, promo: true, promo_dates: true,
        financement: true, labels: ['Label bio Ecocert'], garantie: true, video: [{ controles: true, duree: 32 }, { controles: false, duree: null }],
      });
      assert.deepEqual(a.epuise, { variantes_indisponibles: 3, texte: ['50 ml - épuisé', '', 'Indisponible'] });
      assert.deepEqual(a.impression_produit, { entete_visible: false, nav_visible: true });
      assert.deepEqual(a.panier, { articles_dans_panier: 2, lignes: 2, ajouts_non_demandes: true, lien_vers_article: true, quantite_modifiable: true, suppression: true, sous_total: true, frais_livraison: true, taxes: true, delai: true });
      assert.deepEqual(Object.keys(a.pages), ['https://a.test/collections/all', 'https://a.test/blogs/news']);
      assert.equal(a.pages['https://a.test/collections/all'].gabarit, 'Collection');
      assert.equal(a.pages['https://a.test/collections/all'].copyright, false);
      assert.deepEqual(a.pages['https://a.test/blogs/news'], { gabarit: 'Blog', erreur: 'net::ERR_ABORTED' });
      // ajout au panier : variante disponible, une unité, à la racine localisée
      const ajout = r.journal.find(x => x[0] === 'fetch' && x[1] === 'https://a.test/fr/cart/add.js');
      assert.equal(ajout[2], 'POST'); assert.deepEqual(JSON.parse(ajout[3]), { items: [{ id: 2, quantity: 1 }] });
      assert.ok(r.journal.some(x => x[0] === 'clic' && x[1] === 'button:has-text("Tout refuser")'));
      assert.ok(!r.journal.some(x => x[0] === 'goto' && x[1] === 'https://a.test/account'));  // écran Compte jamais ouvert
      assert.equal(r.journal.filter(x => x[0] === 'goto' && x[1] === 'https://a.test/cart').length, 1);  // panier ouvert une fois, après l'ajout
      // B : popup repérée par son texte, fermeture hors de la popup ; pas de pied de page
      const b = j.B;
      assert.deepEqual(b.popup, { presente: true, texte: 'Code -10 % offert Non merci', bouton_fermer: true, libelle_fermer: 'Non merci', fermer_dans_la_popup: false, frequence_annoncee: false });
      assert.equal(b.pied_de_page, '');
      assert.deepEqual(Object.keys(b.legales), ['https://b.test/pages/livraison']);
      assert.deepEqual(b.page_404, { menu: false, liens_entete: 0 });
      assert.equal(b.mesures_accueil.copyright, true); assert.equal(b.mesures_accueil.nouveautes, true);
      assert.deepEqual(b.impression_accueil, { entete_visible: null, nav_visible: null, pied_visible: null });
      assert.deepEqual(b.impression_produit, { entete_visible: null, nav_visible: false });
      assert.equal(b.produit.prix, '');
      // ajout accepté mais cart.js illisible : panier relevé avec des valeurs par défaut
      assert.deepEqual(b.panier, { articles_dans_panier: null, lignes: 0, ajouts_non_demandes: false, lien_vers_article: false, quantite_modifiable: false, suppression: false, sous_total: false, frais_livraison: false, taxes: false, delai: false });
      assert.deepEqual(JSON.parse(r.journal.find(x => x[0] === 'fetch' && x[1] === 'https://b.test/cart/add.js')[3]), { items: [{ id: 3, quantity: 1 }] });
      // F : erreur sur la fiche produit, relevé non fini
      assert.equal(j.F.erreur, 'boom'); assert.equal(j.F.fini, undefined); assert.deepEqual(j.F.popup, { presente: false });
      assert.equal(j.F.mesures_accueil.nouveautes, false); assert.equal(j.F.page_404.code, 404);
      assert.match(r.sortie, /^A légales 5, popup true, 404 menu true, panier ok$/m);
      assert.match(r.sortie, /^B légales 1, popup true, 404 menu false, panier ok$/m);
      assert.match(r.sortie, /^D page\.goto: net::ERR_NAME_NOT_RESOLVED$/m);
      assert.ok(r.sortie.trim().endsWith(`resultats/releve-${DATE()}/releve.json`));
      assert.ok(r.journal.some(x => x[0] === 'nav.close'));
    } finally { r.nettoyer(); }
  });

  test('releve_regles : --service, popup sans bouton de fermeture, ajout impossible', () => {
    const r = lancer(import.meta.url, 'releve_regles.mjs', 'seul', { args: t => [join(t, 'textes'), '--service', 'E'] });
    try {
      assert.equal(r.statut, 0, r.erreurs);
      const j = r.lire(sortie);
      assert.deepEqual(Object.keys(j), ['E']);
      assert.deepEqual(j.E.popup, { presente: true, texte: 'Inscription', bouton_fermer: false, libelle_fermer: null, fermer_dans_la_popup: false, frequence_annoncee: false });
      assert.equal(j.E.impression_accueil.entete_visible, false);
      assert.equal(j.E.panier, undefined); assert.equal(j.E.fini, true);
      assert.deepEqual(j.E.legales, {});
      assert.ok(r.existe('textes'));
      assert.match(r.sortie, /^E légales 0, popup true, 404 menu false, panier -$/m);
    } finally { r.nettoyer(); }
  });
}
