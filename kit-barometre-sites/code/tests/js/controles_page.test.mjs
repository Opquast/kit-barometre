// Tests de scripts/controles_page.js : pages HTML de test dans jsdom, requêtes HEAD simulées.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fenetre, executer } from './aide_navigateur.mjs';

const SCRIPT = 'controles_page.js';
const C = 'conforme', NC = 'non-conforme', NA = 'non-applicable', NT = 'non-testé';

async function controler(html, { url, avant } = {}) {
  const w = fenetre(html, { url });
  const requetes = [];
  w.fetch = async (u, options) => { requetes.push({ u, options }); return { status: 200 }; };
  if (avant) avant(w, requetes);
  const r = await executer(SCRIPT, w);
  return { r, w, requetes, statut: n => r.resultats[n][0], detail: n => r.resultats[n][1] };
}

function verifier(res, attendus) {
  for (const [n, statut] of Object.entries(attendus)) assert.equal(res.statut(n), statut, `règle ${n} : ${res.detail(n)}`);
}

// Page de produit soignée : tout ce qui se mesure est conforme.
const PAGE_CONFORME = `<!doctype html><html lang="fr"><head>
<meta charset="utf-8"><title>Robe en lin — Boutique</title>
<meta name="description" content="Robe en lin lavé, fabriquée en France.">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="shortcut icon" href="/favicon.ico">
<style>body { color: black } @media screen { p { color: #222 } } @media print { nav { display: none } }</style>
</head><body>
<a href="#contenu">Aller au contenu</a>
<header><nav><a href="/" aria-current="page">Accueil</a> <a href="/pages/contact">Contact</a></nav></header>
<nav aria-label="Fil d'Ariane"><a href="/collections">Collections</a></nav>
<form action="/search" role="search"><label for="q">Rechercher</label><input id="q" type="search" name="q"></form>
<form action="/compte" method="post">
  <label for="e">E-mail</label><input id="e" type="email" name="email" autocomplete="email">
  <label for="p">Mot de passe</label><input id="p" type="password" name="password" autocomplete="current-password">
  <button>Se connecter</button>
</form>
<main id="contenu"><h1>Robe en lin</h1><h2>Description</h2>
<p>Service client : 01 23 45 67 89, <a href="tel:+33123456789">appeler</a>, <a href="mailto:aide@boutique.fr">écrire</a>.</p>
<img src="/logo.png" alt="Boutique">
<a href="/panier" aria-label="Panier"></a>
<span id="lbl-compte">Mon compte</span><a href="/compte" aria-labelledby="lbl-compte"></a>
<a href="/marque"><img src="/m.png" alt="La marque"></a>
<a href="/favoris"><svg aria-label="Favoris"><title></title></svg></a>
<a href="/aide" title="Aide"></a>
<a href="/guide.pdf" target="_blank" title="nouvelle fenêtre">Guide d'entretien (PDF, 2 Mo)</a>
<a href="/cache" target="_blank" style="display:none">caché</a>
<button disabled>Épuisé</button>
<iframe title="Vidéo de présentation" src="https://player.vimeo.com/video/1"></iframe>
<video controls><track kind="captions" src="/s.vtt"></video>
<video autoplay loop muted></video>
<table><caption>Tailles</caption><tr><th scope="col">Taille</th><th id="col-prix">Prix</th></tr><tr><td>S</td><td>10</td></tr></table>
<table aria-label="Stock"><tr><th scope="row">S</th><td>3</td></tr></table>
</main>
<footer><a href="/policies/privacy-policy">Politique de confidentialité</a> <a href="/policies/terms-of-service">CGV</a> <a href="/sitemap">Plan du site</a></footer>
</body></html>`;

test('page soignée : règles conformes, non testées ou non applicables comme attendu', async () => {
  const res = await controler(PAGE_CONFORME, {
    url: 'https://www.boutique.fr/products/robe',
    avant: w => { w.__BRUT = { taille: 5000, fin_meta_charset: 300, declarations: 1 }; },
  });
  verifier(res, {
    3: C, 13: NA, 15: C, 27: C, 28: C, 46: C, 69: C, 92: C, 95: C, 97: C, 98: C, 102: C, 104: C,
    105: C, 107: C, 116: C, 119: C, 120: C, 121: NT, 122: NT, 124: C, 125: NA, 128: C, 130: C, 136: C,
    145: C, 146: C, 147: C, 148: C, 240: NT, 152: C, 155: C, 156: C, 157: C, 164: C, 168: C, 169: C,
    170: NA, 171: C, 186: C, 190: C, 191: C, 193: C, 194: C, 195: C, 232: C, 233: C, 234: C, 236: C,
    237: C, 238: C, 239: C, 242: C, 243: C,
  });
  assert.equal(res.detail(3), 'meta description : 38 caractères');
  assert.equal(res.detail(27), '1 formulaire(s) sensible(s), 0 envoyé(s) en HTTP');
  assert.equal(res.detail(69), '3 champ(s), dont 0 masqué(s) au chargement ; 0 sans étiquette');
  assert.equal(res.detail(107), 'Moyens de contact trouvés : téléphone oui, e-mail oui, page contact oui');
  assert.equal(res.detail(232), "Meta charset terminée à l'octet 300 (limite 1 024)");
  assert.equal(res.detail(195), "Styles d'impression trouvés");
  assert.equal(res.detail(156), "Fil d'Ariane trouvé");
  // Requêtes HEAD : liens internes sans ancre, dédoublonnés, jamais les liens externes ni mailto/tel.
  assert.ok(res.requetes.length > 0);
  for (const { u, options } of res.requetes) {
    assert.ok(u.startsWith('https://www.boutique.fr/') && !u.includes('#'), u);
    assert.equal(options.method, 'HEAD');
    assert.equal(options.redirect, 'follow');
  }
  assert.equal(new Set(res.requetes.map(q => q.u)).size, res.requetes.length);
  assert.equal(res.r.url, 'https://www.boutique.fr/products/robe');
  assert.equal(res.r.version, 'controles_page.js 0.2.0');
  assert.ok(!Number.isNaN(Date.parse(res.r.date)));
});

// Page négligée, servie en HTTP : un maximum de non-conformités.
const PAGE_NON_CONFORME = `<!doctype html><html oncontextmenu="return false"><head>
<title>Produit</title><meta property="og:site_name" content="Ma Marque">
<meta name="viewport" content="user-scalable=no">
<meta http-equiv="refresh" content="30">
<style>p { color: red }</style>
<script type="application/ld+json">{"@type":"Product"}</script>
</head><body oncopy="return false" oncontextmenu="return false">
<textarea oncopy="return false"></textarea>
<input type="tel" name="x" style="display:none" data-largeur="0">
<form action="/s" method="get"><input name="card_number"></form>
<form method="post" id="f2"><input type="password" name="pw"></form>
<input type="text" name="email" onpaste="return false">
<label for="l6"> </label><input id="l6" name="ville" aria-label="Ville">
<span id="lbl">Nom</span><input name="nom" aria-labelledby="lbl" autocomplete="tel">
<input name="zip" title="Code postal">
<input name="q2" id="q2">
<input name="inactif" disabled>
<div aria-hidden="true"><input name="masque"><button disabled>Payer</button><img src="/h.png"><a href="/masque"></a></div>
<div inert><input name="inerte"></div>
<input name="horsfocus" tabindex="-1">
<span aria-disabled="true">Indisponible</span>
<a href="/vide"></a>
<a href="/cache" data-largeur="0"></a>
<a href="/x" aria-labelledby="absent"></a>
<a href="https://autre.fr/e"></a>
<a href="https://ext.fr/" target="_blank">Partenaire</a>
<a href="/doc.docx">Télécharger</a>
<a href="tel:0123456789">Appeler</a>
<a href="http://[">cassé</a>
<a href="/e404">a</a> <a href="/e429">b</a> <a href="/e500">c</a> <a href="/erreur-reseau">d</a>
<button data-largeur="20">ok</button>
<p data-police="Arial">Appelez le 01 23 45 67 89 <a href="/dans-texte" data-hauteur="10">ici</a></p>
<p data-alignement="justify">Un long paragraphe justifié qui dépasse largement les quatre-vingts caractères demandés par le contrôle.</p>
<div data-alignement="justify">court</div>
<img src="/a.jpg"><img src="/b.jpg" role="presentation">
<img src="/grande.jpg" alt="Grande" id="grande"><img src="/charge.jpg" alt="En cours" id="encours"><img src="/zero.jpg" alt="Sans largeur" id="zero">
<iframe src="https://www.youtube.com/embed/x"></iframe>
<iframe aria-label="Carte" src="about:blank"></iframe>
<iframe style="display:none"></iframe><iframe style="visibility:hidden"></iframe><iframe data-hauteur="0"></iframe>
<video autoplay controls></video>
<audio autoplay src="/a.mp3"></audio>
<h1 id="dup">Titre</h1><h2 style="display:none">caché</h2><h3 id="dup">Sous-titre</h3><h1>Encore</h1>
<table><tr><th>A</th></tr></table><table><tr><td>sans en-tête</td></tr></table><table data-largeur="0"><tr><th>caché</th></tr></table>
</body></html>`;

test('page négligée en HTTP : non-conformités détectées, avec le détail attendu', async () => {
  const res = await controler(PAGE_NON_CONFORME, {
    url: 'http://www.boutique.fr/produits/y',
    avant: (w, requetes) => {
      const d = w.document;
      Object.defineProperty(d.getElementById('f2'), 'action', { value: '' });
      Object.defineProperty(d.getElementById('q2'), 'labels', { value: null });
      Object.assign(w, { devicePixelRatio: 0 });
      Object.defineProperties(d.getElementById('grande'), { complete: { value: true }, naturalWidth: { value: 1000 }, clientWidth: { value: 100 } });
      Object.defineProperties(d.getElementById('encours'), { complete: { value: false }, naturalWidth: { value: 1000 }, clientWidth: { value: 100 } });
      Object.defineProperties(d.getElementById('zero'), { naturalWidth: { value: 1000 }, clientWidth: { value: 0 } });
      const feuilles = [...d.styleSheets, { get cssRules() { throw new w.DOMException('feuille externe', 'SecurityError'); } }];
      Object.defineProperty(d, 'styleSheets', { value: feuilles });
      Object.defineProperty(d, 'characterSet', { value: 'windows-1252' });
      w.__BRUT = { taille: 100, fin_meta_charset: 2000, declarations: 2 };
      w.fetch = async (u, options) => {
        requetes.push({ u, options });
        if (u.endsWith('/erreur-reseau')) throw new TypeError('Failed to fetch');
        const code = /\/e(\d{3})$/.exec(u);
        return { status: code ? +code[1] : 200 };
      };
    },
  });
  verifier(res, {
    3: NC, 13: NA, 15: NC, 27: NC, 28: NC, 46: NC, 69: NC, 92: NC, 95: NC, 97: NC, 98: NC, 102: NC, 104: NC,
    105: C, 107: NC, 116: NC, 119: NC, 120: NC, 121: NT, 122: NC, 124: NC, 125: NC, 128: NC, 130: NC, 136: NC,
    145: C, 146: NC, 147: NC, 148: NC, 240: NA, 152: NC, 155: NC, 156: NC, 157: NC, 164: NC, 168: NC, 169: NT,
    170: NA, 171: NC, 186: NC, 190: NC, 191: NC, 193: NC, 194: NC, 195: NC, 232: NC, 233: NC, 234: NC, 236: NC,
    237: NC, 238: NC, 239: NC, 242: NC, 243: NC,
  });
  assert.equal(res.detail(3), 'Aucune meta description');
  assert.equal(res.detail(27), '2 formulaire(s) sensible(s), 2 envoyé(s) en HTTP');
  assert.equal(res.detail(28), "1 formulaire(s) sensible(s) en méthode GET (données dans l'URL)");
  assert.equal(res.detail(69), '9 champ(s), dont 1 masqué(s) au chargement ; 6 sans étiquette (textarea, input[name=x] (masqué au chargement), input[name=card_number])');
  assert.equal(res.detail(92), '2 champ(s) avec onpaste ou oncopy');
  assert.equal(res.detail(95), '3 champ(s) e-mail, téléphone ou recherche déclarés en type text');
  assert.equal(res.detail(97), '5 champ(s) personnel(s), 4 sans attribut autocomplete');
  assert.equal(res.detail(98), "2 bouton(s) désactivé(s), 1 masqué(s) aux lecteurs d'écran");
  assert.equal(res.detail(102), 'Titre : « Produit »');
  assert.equal(res.detail(105), 'Numéro de téléphone présent dans la page');
  assert.equal(res.detail(116), '6 image(s), 1 sans attribut alt');
  assert.equal(res.detail(119), "1 image(s) chargée(s) plus de 3 fois plus large(s) qu'affichée(s)");
  assert.equal(res.detail(120), '2 iframe(s) visible(s), 1 sans titre');
  assert.equal(res.detail(122), '2 vidéo(s), 1 avec son et sans piste de sous-titres');
  assert.equal(res.detail(125), '1 son(s) en lecture automatique');
  assert.equal(res.detail(128), '1 lien(s) tel:, 1 sans indicatif international');
  assert.equal(res.detail(130), 'lang=""');
  assert.equal(res.detail(136), '4 lien(s) sans intitulé sur 14 (/vide, /cache (masqué), /x)');
  assert.equal(res.detail(146), '1 lien(s) en nouvelle fenêtre, 1 sans avertissement');
  assert.equal(res.detail(152), '10 lien(s) interne(s) testé(s), 2 cassé(s) 404 http://www.boutique.fr/e404 ; 500 http://www.boutique.fr/e500');
  assert.equal(res.detail(156), "Aucun fil d'Ariane");
  assert.equal(res.detail(168), 'Aucun moteur de recherche');
  assert.equal(res.detail(186), "14 élément(s) cliquable(s) hors texte, 1 de moins de 24 x 24 px");
  assert.equal(res.detail(190), '2 pile(s) de polices, 1 sans famille générique finale');
  assert.equal(res.detail(191), '1 bloc(s) de texte justifié(s)');
  assert.equal(res.detail(193), 'viewport : « user-scalable=no »');
  assert.equal(res.detail(195), "Aucun style d'impression lisible");
  assert.equal(res.detail(232), "Meta charset terminée à l'octet 2000 (limite 1 024) ; 2 déclarations");
  assert.equal(res.detail(233), 'Codage : windows-1252');
  assert.equal(res.detail(234), '2 h1, 3 titre(s), 1 saut(s) de niveau');
  assert.equal(res.detail(236), '1 identifiant(s) en double dup');
  assert.equal(res.detail(237), 'user-select du corps : auto');
});

test('page d’accueil minimale : règles sans objet non applicables, rien ne casse sans liens ni champs', async () => {
  const res = await controler(`<!doctype html><html oncontextmenu="return false"><head><title>Boutique</title>
    <meta charset="utf-8"><meta name="viewport" content="maximum-scale=1"><meta name="description" content="">
    <meta property="og:site_name"></head><body data-selection="none"><p>Bienvenue</p></body></html>`,
  { url: 'https://www.boutique.fr/' });
  verifier(res, {
    3: NC, 13: NA, 27: NA, 28: NA, 69: NA, 92: NA, 95: NA, 97: NA, 98: NA, 102: C, 104: NC, 105: NC, 107: NC,
    116: NA, 119: NA, 120: NA, 121: NA, 122: NA, 124: NA, 125: NA, 128: NA, 130: NC, 136: C, 145: NA, 146: NA,
    147: NA, 148: NA, 240: NA, 152: C, 155: NC, 156: NA, 164: NC, 168: NC, 169: NT, 170: NA, 186: C, 193: NC,
    194: NC, 232: C, 237: NC, 238: NC, 239: C, 242: NA, 243: NA,
  });
  assert.equal(res.detail(105), 'Aucun numéro de téléphone dans la page');
  assert.equal(res.detail(121), 'Aucun média audio ou vidéo');
  assert.equal(res.detail(156), "Page d'accueil");
  assert.equal(res.detail(232), 'Meta charset cherchée (position non mesurée : code source brut indisponible)');
  assert.equal(res.detail(237), 'user-select du corps : none');
  assert.equal(res.detail(152), '0 lien(s) interne(s) testé(s), 0 cassé(s) ');
  assert.equal(res.requetes.length, 0);
});

test('page de résultats de recherche : nombre de résultats et champ de recherche, fil d’Ariane JSON-LD', async () => {
  const res = await controler(`<!doctype html><html lang="fr"><head><title>Recherche — Boutique</title>
    <script type="application/ld+json">{"@type":"BreadcrumbList","itemListElement":[]}</script></head>
    <body><input type="search" aria-label="Rechercher"><p>12 résultats pour « robe »</p></body></html>`,
  {
    url: 'https://www.boutique.fr/search?q=robe',
    avant: w => { w.__BRUT = { taille: 3000, fin_meta_charset: null, declarations: 0 }; },
  });
  verifier(res, { 13: C, 156: C, 168: C, 169: NT, 170: C, 232: NC });
  assert.equal(res.detail(168), 'Formulaire de recherche présent');
  assert.equal(res.detail(232), 'Aucune meta charset dans le code source');
});

test('page de recherche sans compteur ni champ, code source brut vide, sans meta charset', async () => {
  const res = await controler('<!doctype html><html><head><title>x</title></head><body><p>Aucun produit trouvé</p></body></html>', {
    url: 'https://www.boutique.fr/fr/search',
    avant: w => { w.__BRUT = { taille: 0 }; },
  });
  verifier(res, { 13: NC, 156: NC, 170: NC, 232: NC });
  assert.equal(res.detail(232), 'Meta charset cherchée (position non mesurée : code source brut indisponible)');
});

test('accueil de langue (/fr) : 30 requêtes HEAD au plus, retour à l’accueil /fr/ reconnu', async () => {
  const liens = Array.from({ length: 35 }, (_, i) => `<a href="/p${i}">Produit ${i}</a>`).join('')
    + '<a href="/p0">doublon</a><a href="/p1#avis">ancre</a><a href="https://ailleurs.fr/z">externe</a><a href="/fr/">Accueil</a>';
  const res = await controler(`<!doctype html><html lang="fr"><head><title>Boutique</title></head><body>${liens}</body></html>`, {
    url: 'https://www.boutique.fr/fr',
  });
  assert.equal(res.requetes.length, 30);
  assert.equal(res.requetes[0].u, 'https://www.boutique.fr/p0');
  assert.equal(res.requetes[29].u, 'https://www.boutique.fr/p29');
  verifier(res, { 152: C, 155: C, 156: NA });
  assert.equal(res.detail(152), '30 lien(s) interne(s) testé(s), 0 cassé(s) ');
});

test('formulaire de recherche en POST non conforme à 169 ; e-mail trouvé dans le texte, numéro sans lien tel:', async () => {
  const res = await controler(`<!doctype html><html lang="fr"><head><title>Boutique</title></head><body>
    <form action="/search" method="POST"><input type="search" name="q" aria-label="Rechercher"></form>
    <p>Écrivez à aide@boutique.fr ou appelez le 01 23 45 67 89.</p></body></html>`);
  verifier(res, { 168: C, 169: NC, 105: C, 107: C, 128: NC, 145: NC });
  assert.equal(res.detail(107), 'Moyens de contact trouvés : téléphone oui, e-mail oui, page contact non');
});

test('cas limites : lien href vide sans intitulé, formulaire sensible sans attribut method (GET par défaut), champ texte sans nom', async () => {
  const res = await controler(`<!doctype html><html lang="fr"><head><title>Boutique</title></head><body>
    <a href=""></a>
    <form><input type="password" aria-label="Mot de passe"><input type="text" aria-label="Pseudo"></form></body></html>`,
  { url: 'https://www.boutique.fr/compte' });
  verifier(res, { 27: C, 28: NC, 95: C, 136: NC });
  assert.equal(res.detail(28), "1 formulaire(s) sensible(s) en méthode GET (données dans l'URL)");
  assert.equal(res.detail(136), '1 lien(s) sans intitulé sur 1');
  // href="" désigne la page elle-même : testée en HEAD.
  assert.deepEqual(res.requetes.map(q => q.u), ['https://www.boutique.fr/compte']);
});

test('règle 125 : un son présent sans lecture automatique est compté non conforme (défaut connu du script)', async () => {
  // Le script ne peut jamais rendre « conforme » pour 125 (branche morte, ligne marquée node:coverage ignore).
  const res = await controler('<!doctype html><html lang="fr"><head><title>Boutique</title></head><body><audio controls src="/a.mp3"></audio></body></html>');
  assert.equal(res.statut(125), NC);
  assert.equal(res.detail(125), '0 son(s) en lecture automatique');
});
