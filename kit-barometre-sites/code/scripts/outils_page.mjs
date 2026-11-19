// Outils du support J2, page par page, avec Playwright (Chromium) : lecture seule, aucune action sur les sites.
//
// - EcoIndex : taille du DOM, nombre de requêtes et poids transféré (après défilement jusqu'en bas), puis note
//   A à G calculée avec la formule publiée par GreenIT et le collectif Conception responsable de service numérique
//   (quantiles de référence ci-dessous). GES et eau estimés par la même méthode.
// - IBM Equal Access Checker (moteur accessibility-checker-engine, open source) : second avis indépendant d'axe-core.
// - Traceurs avant consentement (méthode DevTools du support J2, comme Blacklight) : sur l'accueil, contexte vierge,
//   aucun clic ; cookies déposés (noms et domaines, jamais les valeurs) et appels vers des domaines tiers connus.
// - Lighthouse (performance, accessibilité, bonnes pratiques, SEO) : sur accueil, collection, produit et panier.
//
// Usage : node scripts/outils_page.mjs [--service "Boutique A"] [--sans-lighthouse]
// Sortie : resultats/outils-AAAA-MM-JJ/pages.json
import { chromium } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';

const RACINE = new URL('..', import.meta.url).pathname;
const pause = ms => new Promise(ok => setTimeout(ok, ms));
const args = process.argv.slice(2);
const seul = args.includes('--service') ? args[args.indexOf('--service') + 1] : null;
const ACE = `${RACINE}node_modules/accessibility-checker-engine/ace.js`;

// Quantiles de référence de l'EcoIndex (GreenIT-Analysis, ecoindex.fr).
const Q_DOM = [0, 47, 75, 159, 233, 298, 358, 417, 476, 537, 603, 674, 753, 843, 949, 1076, 1237, 1459, 1801, 2479, 594601];
const Q_REQ = [0, 2, 15, 25, 34, 42, 49, 56, 63, 70, 78, 86, 95, 105, 117, 130, 147, 170, 205, 281, 3920];
const Q_SIZE = [0, 1.37, 144.7, 319.53, 479.46, 631.97, 783.38, 937.91, 1098.62, 1265.47, 1448.32, 1648.27, 1876.08, 2142.06, 2465.37, 2866.31, 3401.59, 4155.73, 5400.08, 8037.54, 223212.26];
const quantile = (q, v) => { for (let i = 1; i < q.length; i++) if (v < q[i]) return i - 1 + (v - q[i - 1]) / (q[i] - q[i - 1]); return q.length - 1; };
function ecoindex(dom, req, kb) {
  const s = 100 - 5 * (3 * quantile(Q_DOM, dom) + 2 * quantile(Q_REQ, req) + quantile(Q_SIZE, kb)) / 6;
  const note = s > 80 ? 'A' : s > 70 ? 'B' : s > 55 ? 'C' : s > 40 ? 'D' : s > 25 ? 'E' : s > 10 ? 'F' : 'G';
  return { score: Math.round(s * 10) / 10, note, ges_g: Math.round((2 + 2 * (50 - s) / 100) * 100) / 100, eau_cl: Math.round((3 + 3 * (50 - s) / 100) * 100) / 100 };
}
const TRACEURS = /google-analytics|googletagmanager|doubleclick|googleadservices|googlesyndication|facebook\.(com|net)|connect\.facebook|tiktok|analytics\.tiktok|pinterest|pinimg|snapchat|sc-static|hotjar|clarity\.ms|bing\.com|criteo|taboola|outbrain|adroll|linkedin|licdn|twitter|ads-twitter|quantserve|scorecardresearch|yandex|mouseflow|contentsquare|matomo|segment\.|mixpanel|amplitude|heap|fullstory|klaviyo|trustpilot|yotpo|gorgias|attentive|privy|omnisend|sendinblue|brevo|axeptio|didomi|onetrust|cookiebot|tarteaucitron/i;

function lireCsv(chemin) {
  const [tete, ...lignes] = readFileSync(chemin, 'utf8').trim().split('\n');
  const cols = tete.split(',');
  return lignes.map(l => {
    const v = l.match(/("([^"]|"")*"|[^,]*)(,|$)/g).map(x => x.replace(/,$/, '').replace(/^"|"$/g, '').replace(/""/g, '"'));
    return Object.fromEntries(cols.map((c, i) => [c, v[i]]));
  });
}

const ecrans = lireCsv(`${RACINE}scripts/ecrans_en_ligne.csv`).filter(e => !seul || e.service === seul);
const date = new Date().toISOString().slice(0, 10);
const dossier = `${RACINE}resultats/outils-${date}`;
mkdirSync(dossier, { recursive: true });
const fichier = `${dossier}/pages.json`;
const res = existsSync(fichier) ? JSON.parse(readFileSync(fichier, 'utf8')) : {};
const sauver = () => writeFileSync(fichier, JSON.stringify(res, null, 1));
const navigateur = await chromium.launch();

// 1. Traceurs avant consentement, accueil de chaque site, contexte vierge.
for (const nom of [...new Set(ecrans.map(e => e.service))]) {
  const s = (res[nom] ??= { pages: {} });
  if (s.traceurs) continue;
  const accueil = ecrans.find(e => e.service === nom && e.gabarit.startsWith('Accueil')).url;
  const ctx = await navigateur.newContext({ viewport: { width: 1280, height: 900 }, locale: 'fr-FR' });
  const page = await ctx.newPage();
  const tiers = new Set();
  const hote = new URL(accueil).hostname.replace(/^www\./, '');
  page.on('request', r => { try { const h = new URL(r.url()).hostname; if (!h.endsWith(hote) && !/shopify|shopifycdn|cdn\.shopify/.test(h)) tiers.add(h); } catch {} });
  try {
    await page.goto(accueil, { waitUntil: 'load', timeout: 45000 });
    await pause(8000);
    const cookies = (await ctx.cookies()).map(c => ({ nom: c.name, domaine: c.domain }));
    const tiersL = [...tiers].sort();
    const bandeau = await page.evaluate(() => !!document.querySelector('[id*=cookie i], [class*=cookie i], [id*=consent i], [class*=consent i], #axeptio_overlay, #didomi-host, #onetrust-banner-sdk, #CybotCookiebotDialog, #tarteaucitronRoot, .shopify-pc__banner'));
    s.traceurs = { cookies_avant_consentement: cookies.length, cookies: cookies.slice(0, 60),
      cookies_de_mesure: cookies.filter(c => /^_ga|_gid|_gcl|_fbp|_fbc|_tt|_pin|_scid|_hj|_clck|_clsk|_uet|ajs_|mp_|_ttp|__kla_id|_shopify_y|_shopify_s|_orig_referrer|_landing_page/i.test(c.nom)).map(c => c.nom),
      domaines_tiers: tiersL.length, traceurs_connus: tiersL.filter(h => TRACEURS.test(h)), bandeau_consentement: bandeau };
  } catch (err) { s.traceurs = { erreur: String(err.message).split('\n')[0] }; }
  await ctx.close();
  console.log(nom, 'traceurs', JSON.stringify(s.traceurs).slice(0, 200));
  sauver();
  await pause(6000);
}

// 2. EcoIndex et IBM Equal Access, page par page.
for (const e of ecrans) {
  const s = (res[e.service] ??= { pages: {} });
  if (s.pages[e.url]?.ecoindex && s.pages[e.url]?.ibm) continue;
  const ctx = await navigateur.newContext({ viewport: { width: 1920, height: 1080 }, locale: 'fr-FR' });
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  let octets = 0, requetes = 0;
  cdp.on('Network.loadingFinished', ev => { octets += ev.encodedDataLength; requetes++; });
  const p = (s.pages[e.url] = { gabarit: e.gabarit });
  try {
    const rep = await page.goto(e.url, { waitUntil: 'load', timeout: 45000 });
    if (new URL(page.url()).hostname !== new URL(e.url).hostname) throw new Error('quitte le site : compte client hébergé par Shopify');
    if (!rep || rep.status() >= 400) throw new Error(`code ${rep ? rep.status() : '?'}`);
    await pause(3000);
    await page.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 800) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 150)); } });
    await pause(3000);
    const dom = await page.evaluate(() => [...document.getElementsByTagName('*')].filter(x => !x.closest('svg') || x.tagName.toLowerCase() === 'svg').length);
    const kb = octets / 1024;
    p.ecoindex = { dom, requetes, poids_ko: Math.round(kb), ...ecoindex(dom, requetes, kb) };
    await page.addScriptTag({ path: ACE });
    const ibm = await page.evaluate(async () => {
      const r = await new window.ace.Checker().check(document, ['IBM_Accessibility']);
      const v = r.results.filter(x => x.value[0] === 'VIOLATION' && x.value[1] === 'FAIL');
      const parRegle = {};
      for (const x of v) parRegle[x.ruleId] = (parRegle[x.ruleId] || 0) + 1;
      return { violations: v.length, regles: Object.keys(parRegle).length, par_regle: parRegle,
        a_verifier: r.results.filter(x => x.value[0] === 'VIOLATION' && x.value[1] === 'POTENTIAL').length };
    });
    p.ibm = ibm;
  } catch (err) { p.non_teste = String(err.message).split('\n')[0]; }
  await ctx.close();
  console.log(e.service, '|', e.gabarit, '|', p.non_teste || `EcoIndex ${p.ecoindex.note} (${p.ecoindex.score}), IBM ${p.ibm.violations} violations`);
  sauver();
  await pause(6000);
}
await navigateur.close();

// 3. Lighthouse sur 4 gabarits par site.
if (!args.includes('--sans-lighthouse')) {
  const { default: lighthouse } = await import('lighthouse');
  const chromeLauncher = await import('chrome-launcher');
  const chrome = await chromeLauncher.launch({ chromePath: chromium.executablePath(), chromeFlags: ['--headless=new', '--no-sandbox'] });
  for (const e of ecrans.filter(x => /^(Accueil|Collection|Produit|Panier)/.test(x.gabarit))) {
    const p = res[e.service].pages[e.url];
    if (p.lighthouse && (p.lighthouse.audits || !args.includes('--audits-lighthouse'))) continue;
    try {
      const r = await lighthouse(e.url, { port: chrome.port, output: 'json', logLevel: 'error', onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'] });
      const c = r.lhr.categories;
      if (r.lhr.runtimeError) throw new Error(r.lhr.runtimeError.message);
      p.lighthouse = { performance: Math.round(c.performance.score * 100), accessibilite: Math.round(c.accessibility.score * 100),
        bonnes_pratiques: Math.round(c['best-practices'].score * 100), seo: Math.round(c.seo.score * 100),
        lcp_s: Math.round(r.lhr.audits['largest-contentful-paint'].numericValue / 100) / 10, cls: Math.round(r.lhr.audits['cumulative-layout-shift'].numericValue * 1000) / 1000,
        tbt_ms: Math.round(r.lhr.audits['total-blocking-time'].numericValue) };
      // audits reliés à des règles Opquast (recoupement avec nos scripts) : score 1 = réussi, 0 = échoué, null = sans objet
      p.lighthouse.audits = Object.fromEntries(['meta-description', 'image-alt', 'link-name', 'color-contrast', 'viewport', 'is-on-https',
        'uses-text-compression', 'uses-long-cache-ttl', 'unminified-css', 'unminified-javascript', 'uses-responsive-images', 'document-title', 'html-has-lang', 'label']
        .filter(k => r.lhr.audits[k]).map(k => [k, r.lhr.audits[k].score]));
    } catch (err) { p.lighthouse = { erreur: String(err.message).split('\n')[0] }; }
    console.log(e.service, '|', e.gabarit, '| Lighthouse', JSON.stringify(p.lighthouse));
    sauver();
    await pause(8000);
  }
  await chrome.kill();
}
console.log(fichier);
