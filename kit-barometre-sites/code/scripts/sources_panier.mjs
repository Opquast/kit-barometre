// Deuxième source pour le panier et la page de paiement (13/11) : l'API Ajax publique de Shopify, documentée
// (shopify.dev/docs/api/ajax), plutôt que la lecture de la page du relevé. Aucune saisie, aucune commande, aucun
// paiement : un article est ajouté au panier de la session de test (comme au relevé), puis la page de paiement est
// seulement affichée et capturée (texte et image gardés HORS du dépôt) pour une lecture visuelle indépendante.
//
// Règles tranchées ici : 31 (lien vers l'article depuis le panier : items[].url), 32 (rien d'ajouté sans action :
// item_count après un seul ajout), 38 (quantité modifiable : la ligne a une quantité et une clé modifiables par
// /cart/change.js, vérifié sans l'appeler), 41 (sous-total détaillé : prix de ligne et total), 35 et 36 (délai et
// frais de livraison estimés : /cart/shipping_rates.json pour une adresse de test à Paris), 30 (achat sans compte :
// la page de paiement s'ouvre sans connexion).
//
// Usage : node scripts/sources_panier.mjs <dossier hors dépôt>
// Sortie : resultats/sources-AAAA-MM-JJ/panier.json  { site: { regle: [statut, preuve, outil] } }
import { chromium } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';

const RACINE = new URL('..', import.meta.url).pathname;
const HORS = process.argv[2];
mkdirSync(`${HORS}/paiement`, { recursive: true });
const pause = ms => new Promise(ok => setTimeout(ok, ms));
const ecrans = readFileSync(`${RACINE}scripts/ecrans_en_ligne.csv`, 'utf8').trim().split('\n').slice(1).map(l => {
  const [service, gabarit, ...u] = l.split(','); return { service, gabarit, url: u.join(',') };
});
const res = {};
const nav = await chromium.launch();
const deja = (() => { try { return JSON.parse(readFileSync(`${RACINE}resultats/sources-${new Date().toISOString().slice(0, 10)}/panier.json`, 'utf8')); } catch { return {}; } })();
for (const nom of [...new Set(ecrans.map(e => e.service))]) {
  if (deja[nom] && !deja[nom]._non_teste) { res[nom] = deja[nom]; continue; }
  const prod = ecrans.find(e => e.service === nom && e.gabarit === 'Produit');
  const r = (res[nom] = {});
  const ctx = await nav.newContext({ viewport: { width: 1280, height: 900 }, locale: 'fr-FR' });
  const page = await ctx.newPage();
  try {
    await page.goto(prod.url, { waitUntil: 'load', timeout: 45000 });
    await pause(3000);
    if (/connexion doit être vérifiée|Just a moment|verify you are human/i.test(await page.evaluate(() => document.body.innerText.slice(0, 600))))
      throw new Error('vérification anti-robot : non contournée');
    // requêtes par le client HTTP de Playwright (même session et mêmes cookies que la page) : certains thèmes
    // modifient window.fetch dans la page
    const base = new URL(prod.url).origin + ((await page.evaluate(() => window.Shopify?.routes?.root)) || '/');
    const rq = ctx.request;
    let vid = null;
    try { const p = await (await rq.get(prod.url.split('?')[0] + '.js')).json(); vid = (p.variants.find(x => x.available) || p.variants[0]).id; } catch {}
    if (!vid) vid = await page.evaluate(() => window.ShopifyAnalytics?.meta?.product?.variants?.[0]?.id || document.querySelector('form[action*="/cart/add"] [name="id"]')?.value);
    if (!vid) throw new Error('article introuvable sur la fiche produit');
    await rq.post(base + 'cart/clear.js');
    const add = await rq.post(base + 'cart/add.js', { data: { items: [{ id: Number(vid), quantity: 1 }] } });
    const cr = await rq.get(base + 'cart.js', { headers: { Accept: 'application/json' } });
    if (!(cr.headers()['content-type'] || '').includes('json')) throw new Error(`cart.js non servi en JSON (code ${cr.status()})`);
    const cart = await cr.json();
    let rates = null;
    const rr = await rq.get(base + 'cart/shipping_rates.json?shipping_address%5Bzip%5D=75001&shipping_address%5Bcountry%5D=France', { headers: { Accept: 'application/json' } });
    try { rates = rr.ok() ? await rr.json() : { erreur: rr.status() }; } catch { rates = { erreur: 'réponse non JSON' }; }
    const api = { ajout: add.status(), cart, rates };
    const it = api.cart.items || [];
    r['32'] = [api.cart.item_count === 1 ? 'C' : 'NC', `après un seul ajout, le panier compte ${api.cart.item_count} article(s) sur ${it.length} ligne(s)`, 'API panier Shopify (cart.js)'];
    r['31'] = [it.every(x => x.url) ? 'C' : 'NC', `ligne du panier : lien vers la fiche « ${(it[0]?.url || 'absent').split('?')[0].slice(0, 60)} »`, 'API panier Shopify (cart.js)'];
    r['38'] = [it.length && it.every(x => x.key && x.quantity >= 1) ? 'C' : 'NC', `ligne modifiable par clé (${it[0]?.key ? 'présente' : 'absente'}), quantité ${it[0]?.quantity}`, 'API panier Shopify (cart.js)'];
    r['41'] = [it.length && it.every(x => typeof x.final_line_price === 'number') && typeof api.cart.total_price === 'number' ? 'C' : 'NC',
      `prix de ligne ${(it[0]?.final_line_price / 100).toFixed(2)} € et total ${(api.cart.total_price / 100).toFixed(2)} € détaillés par l'API`, 'API panier Shopify (cart.js)'];
    const tarifs = api.rates?.shipping_rates;
    if (Array.isArray(tarifs) && tarifs.length) {
      r['36'] = ['C', `${tarifs.length} tarif(s) de livraison estimé(s) pour Paris, dont « ${tarifs[0].name} » à ${tarifs[0].price} €`, 'API panier Shopify (shipping_rates)'];
      const delai = tarifs.filter(t => t.delivery_range || t.delivery_days || /jour|day|\d+-\d+/i.test(t.name || ''));
      r['35'] = [delai.length ? 'C' : 'NC', delai.length ? `délai annoncé : « ${delai[0].name} »${delai[0].delivery_range ? ` (${delai[0].delivery_range.join(' à ')})` : ''}` : 'aucun délai dans les tarifs de livraison', 'API panier Shopify (shipping_rates)'];
    } else r._tarifs = JSON.stringify(api.rates).slice(0, 120);

    // page de paiement : affichée seulement, rien n'est saisi
    await page.goto(new URL(prod.url).origin + (prod.url.includes('/fr/') ? '/fr' : '') + '/checkout', { waitUntil: 'load', timeout: 45000 });
    await pause(6000);
    const u = page.url();
    const connexion = /\/account\/login|\/challenge|shopify\.com\/authentication/.test(u);
    r['30'] = [connexion ? 'NC' : 'C', connexion ? `la page de paiement renvoie vers une connexion (${u.slice(0, 70)})` : 'la page de paiement s\'ouvre sans connexion ni création de compte', 'Page de paiement (affichée)'];
    const slug = nom.replace(/[^A-Za-z0-9_]+/g, '_');
    writeFileSync(`${HORS}/paiement/${slug}.txt`, await page.evaluate(() => document.body.innerText));
    await page.screenshot({ path: `${HORS}/paiement/${slug}.jpg`, type: 'jpeg', quality: 60, fullPage: true }).catch(() => {});
    await page.goto(new URL(prod.url).origin + '/cart', { waitUntil: 'load', timeout: 45000 }).catch(() => {});
    await pause(3000);
    await page.screenshot({ path: `${HORS}/paiement/${slug}__panier.jpg`, type: 'jpeg', quality: 60, fullPage: true }).catch(() => {});
    await ctx.request.post(base + 'cart/clear.js').catch(() => {});
  } catch (err) { r._non_teste = String(err.message).split('\n')[0].slice(0, 140); }
  await ctx.close();
  console.log(nom, r._non_teste || Object.entries(r).filter(([k]) => !k.startsWith('_')).map(([k, v]) => `${k}:${v[0]}`).join(' '), r._tarifs || '');
  await pause(5000);
}
await nav.close();
const d = `${RACINE}resultats/sources-${new Date().toISOString().slice(0, 10)}`; mkdirSync(d, { recursive: true });
writeFileSync(`${d}/panier.json`, JSON.stringify(res, null, 1));
console.log(`${d}/panier.json`);
