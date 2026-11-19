// Outils tiers de confiance, installés avec l'accord de Mattea le 13/11 (versions épinglées, scripts d'installation non
// exécutés) : deuxièmes et troisièmes sources sur les règles Opquast. Lecture seule : aucune saisie, aucun envoi ; le
// seul clic est le refus des cookies (choix le plus protecteur), avant l'impression.
//
// - Moteur officiel Opquast devtools (opquast-oss/opquast-devtools v0.7.2, moteur opquast-test-runner + surcouche V5
//   0.8.0) : verdicts c / nc / na de ses jeux de tests V5. Les 10 jeux hérités de la V3 et sans rapport avec la règle
//   (12, 39, 43, 103, 141, 144, 150, 151, 162, 203 ; benchmark du 12/11) sont ignorés ; « i » (à vérifier) ne compte pas.
// - Siteimprove Alfa 0.120 (règles ACT) : SIA-R62 -> 140, SIA-R65 -> 165, SIA-R41 -> 137, SIA-R1 -> 103.
// - Sa11y 5.1 (Université métropolitaine de Toronto), langue fr : LINK_STOPWORD et LINK_CLICK_HERE -> 137,
//   QA_UNDERLINE -> 139, QA_UPPERCASE -> 192, QA_FAKE_LIST -> 235 (avertissements : un défaut relevé = NC, sinon C).
// - html-validate 11.17 sur le HTML envoyé par le serveur : wcag/h30 -> 117, wcag/h37 -> 118, no-autoplay -> 126,
//   empty-title et long-title -> 103, text-content -> 159, meta-refresh -> 172.
// - Impression réelle après refus des cookies (page.pdf puis pdftotext) : 196.
// - Garde, HORS du dépôt, le DOM rendu et des captures pour la lecture indépendante (dossier passé en argument).
//
// Usage : node scripts/sources_tiers.mjs <moteur devtools public/engine> <dossier hors dépôt> [--service "…"]
// Sortie : resultats/sources-AAAA-MM-JJ/tiers.json  { site: { url: { regle: [[statut, preuve, outil], …] } } }
import { chromium, request } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync, existsSync, rmSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { HtmlValidate } from 'html-validate';
import { Playwright } from '@siteimprove/alfa-playwright';
import { Audit } from '@siteimprove/alfa-act';
import Rules from '@siteimprove/alfa-rules';

const RACINE = new URL('..', import.meta.url).pathname;
const [ENGINE, HORS] = process.argv.slice(2, 4);
const args = process.argv.slice(4);
const seul = args.includes('--service') ? args[args.indexOf('--service') + 1] : null;
const pause = ms => new Promise(ok => setTimeout(ok, ms));
const ecrans = readFileSync(`${RACINE}scripts/ecrans_en_ligne.csv`, 'utf8').trim().split('\n').slice(1).map(l => {
  const [service, gabarit, ...u] = l.split(','); return { service, gabarit, url: u.join(',') };
}).filter(e => !seul || e.service === seul);
const date = new Date().toISOString().slice(0, 10);
const dossier = `${RACINE}resultats/sources-${date}`; mkdirSync(dossier, { recursive: true });
const fichier = `${dossier}/tiers.json`;
const res = existsSync(fichier) ? JSON.parse(readFileSync(fichier, 'utf8')) : {};
mkdirSync(`${HORS}/dom`, { recursive: true }); mkdirSync(`${HORS}/captures`, { recursive: true });

// moteur Opquast
const LIBS = ['jquery-3.7.1.min.js', 'jquery-migrate-3.5.2.min.js', 'oqs-utils.js', 'cssParser.js', 'oqs-validator.js', 'oqs-tests.js', 'oqs-tests-overlay.js'];
const libSources = LIBS.map(f => readFileSync(`${ENGINE}/${f}`, 'utf8'));
const rules = JSON.parse(readFileSync(`${ENGINE}/rules.json`, 'utf8'));
const rulesets = JSON.parse(readFileSync(`${ENGINE}/rulesets.json`, 'utf8'));
const triage = JSON.parse(readFileSync(`${ENGINE}/../../data/v5-automation-triage.json`, 'utf8')).rules;
const ID_NUM = Object.fromEntries(triage.map(r => [r.id, r.num]));
const HORS_SUJET = new Set(['12', '39', '43', '103', '141', '144', '150', '151', '162', '203']);
const SUBSET = Object.fromEntries(Object.entries(rulesets).filter(([id]) => ID_NUM[id] && !HORS_SUJET.has(ID_NUM[id])));

const SA11Y = { LINK_STOPWORD: '137', LINK_CLICK_HERE: '137', QA_UNDERLINE: '139', QA_UPPERCASE: '192', QA_FAKE_LIST: '235' };
const ALFA = { 'sia-r62': '140', 'sia-r65': '165', 'sia-r41': '137', 'sia-r1': '103' };
const HV = { 'wcag/h30': '117', 'wcag/h37': '118', 'no-autoplay': '126', 'empty-title': '103', 'long-title': '103', 'text-content': '159', 'meta-refresh': '172' };
const htmlvalidate = new HtmlValidate({ rules: Object.fromEntries(Object.keys(HV).map(k => [k, 'error'])) });

const ajoute = (r, n, st, preuve, outil) => { if (['C', 'NC', 'NA'].includes(st)) (r[n] ??= []).push([st, preuve.slice(0, 220), outil]); };

let nav = await chromium.launch();
const req = await request.newContext({ userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36' });
for (const e of ecrans) {
  const s = (res[e.service] ??= {});
  if (s[e.url] && !s[e.url]._non_teste) continue;
  const r = (s[e.url] = { _gabarit: e.gabarit });
  const nomf = `${e.service}__${e.gabarit}`.replace(/[^A-Za-z0-9_]+/g, '_').slice(0, 80);
  let ctx;
  try { ctx = await nav.newContext({ viewport: { width: 1280, height: 900 }, locale: 'fr-FR' }); }
  catch { try { await nav.close(); } catch {} nav = await chromium.launch(); ctx = await nav.newContext({ viewport: { width: 1280, height: 900 }, locale: 'fr-FR' }); }
  const page = await ctx.newPage();
  try {
    // html-validate sur le HTML envoyé par le serveur
    const brut = await req.get(e.url, { timeout: 45000 });
    if (brut.status() === 200 && new URL(brut.url()).host === new URL(e.url).host) {
      const rep = await htmlvalidate.validateString(await brut.text());
      const msgs = rep.results.flatMap(x => x.messages);
      for (const [id, n] of Object.entries(HV)) {
        const m = msgs.filter(x => x.ruleId === id);
        ajoute(r, n, m.length ? 'NC' : 'C', m.length ? `${id} : ${m.length} défaut(s), ex. « ${m[0].message} »` : `${id} : aucun défaut`, 'html-validate');
      }
    }
    const rep = await page.goto(e.url, { waitUntil: 'load', timeout: 45000 });
    if (new URL(page.url()).hostname !== new URL(e.url).hostname) throw new Error('quitte le site (compte client hébergé par Shopify)');
    if (!rep || rep.status() >= 400) throw new Error(`code ${rep ? rep.status() : '?'}`);
    await pause(5000);
    if (/cf-challenge|Just a moment|verify you are human|connexion doit être vérifiée/i.test(await page.title() + ' ' + (await page.evaluate(() => document.body?.innerText.slice(0, 600) || ''))))
      throw new Error('vérification anti-robot affichée : non contournée');
    // refus des cookies (choix le plus protecteur), seul clic du passage
    const refus = page.locator('button, a').filter({ hasText: /^(tout refuser|refuser( tout| tous les cookies)?|continuer sans accepter|reject all|decline)$/i }).first();
    if (await refus.count()) { await refus.click({ timeout: 3000 }).catch(() => {}); await pause(1500); }
    // Escape ferme les fenêtres d'inscription qui recouvrent la page
    await page.keyboard.press('Escape').catch(() => {}); await pause(500);

    // moteur Opquast
    const oq = await Promise.race([page.evaluate(async ({ libSources, rules, subset }) => {
      for (const src of libSources) { const sc = document.createElement('script'); sc.textContent = src; document.head.appendChild(sc); sc.remove(); }
      const g = window, $ = g.jQuery;
      const md = () => { let a, b; const p = new Promise((x, y) => { a = x; b = y; }); return { promise: p, resolve: a, reject: b }; };
      g.Q = { defer: md, resolve: v => Promise.resolve(v), reject: e => Promise.reject(e), promised: () => (...ps) => Promise.all(ps) };
      if (typeof g.console.exception !== 'function') g.console.exception = e => g.console.error(e);
      g.dnsLookup = () => Promise.resolve(null);
      g.XHR = { get: () => Promise.resolve({ status: 0, statusText: '', headers: [], content_type: null, data: '', xml: null, getHeader: () => null }), query: () => Promise.resolve({ status: 0, headers: [], data: '' }) };
      g.sidecar = { resources: [], events: [], pageInfo: $.extractPageInfo(), plainText: new XMLSerializer().serializeToString(document) };
      g.tests = rules; g.criteria = subset;
      const arr = await g.analyze(subset).then(x => g.synthesize_results(x));
      return (Array.isArray(arr) ? arr : []).map(x => ({ id: String(x.id ?? x.criterion ?? ''), result: x.result, n: (x.details || []).length, ex: (x.details || []).slice(0, 1).map(d => String(d.comment || d.text || d.message || '').slice(0, 80)) }));
    }, { libSources, rules, subset: SUBSET }), pause(60000).then(() => { throw new Error('moteur Opquast : délai dépassé'); })]).catch(err => ({ erreur: String(err.message).slice(0, 100) }));
    if (Array.isArray(oq)) {
      for (const x of oq) {
        const n = ID_NUM[x.id]; if (!n) continue;
        const st = { c: 'C', nc: 'NC', na: 'NA' }[x.result];
        ajoute(r, n, st, `Moteur Opquast (jeu ${x.id}) : ${x.result}${x.n ? `, ${x.n} élément(s)` : ''}${x.ex[0] ? ` ; ${x.ex[0]}` : ''}`, 'Moteur Opquast devtools');
      }
    } else r._opquast = oq.erreur;

    // Sa11y (langue fr)
    await page.addScriptTag({ path: `${RACINE}node_modules/sa11y/dist/js/sa11y.umd.min.js` });
    await page.addScriptTag({ path: `${RACINE}node_modules/sa11y/dist/js/lang/fr.umd.js` });
    const sa = await page.evaluate(async () => {
      window.Sa11y.Lang.addI18n(window.Sa11yLangFr.strings);
      new window.Sa11y.Sa11y({ headless: true, checkRoot: 'body', detectSPArouting: false });
      for (let i = 0; i < 40 && !window.sa11yCheckComplete; i++) await new Promise(r => setTimeout(r, 250));
      const d = window.sa11yCheckComplete; if (!d) return null;
      const c = {}; for (const x of d.results) { const k = x.test || x.type; c[k] = (c[k] || 0) + 1; } return c;
    }).catch(() => null);
    if (sa) {
      const parN = {};
      for (const [t, n] of Object.entries(SA11Y)) (parN[n] ??= []).push([t, sa[t] || 0]);
      for (const [n, l] of Object.entries(parN)) {
        const tot = l.reduce((a, [, k]) => a + k, 0);
        ajoute(r, n, tot ? 'NC' : 'C', `Sa11y : ${l.map(([t, k]) => `${t} ${k}`).join(', ')}`, 'Sa11y');
      }
    }

    // Siteimprove Alfa
    const alfa = await Promise.race([(async () => {
      const doc = await page.evaluateHandle(() => window.document);
      const alfaPage = await Playwright.toPage(doc);
      const choix = [...Rules].filter(x => Object.keys(ALFA).some(k => x.uri.toLowerCase().endsWith('/' + k)));
      const out = await Audit.of(alfaPage, choix).evaluate();
      const c = {};
      for (const o of out) { const j = o.toJSON(); const k = Object.keys(ALFA).find(k => j.rule.uri.toLowerCase().endsWith('/' + k)); (c[k] ??= {})[j.outcome] = ((c[k] ?? {})[j.outcome] || 0) + 1; }
      return c;
    })(), pause(60000).then(() => null)]).catch(() => null);
    if (alfa) for (const [k, n] of Object.entries(ALFA)) {
      const o = alfa[k] || {};
      const st = o.failed ? 'NC' : o.passed ? 'C' : (o.inapplicable && !o.cantTell) ? 'NA' : null;
      if (st) ajoute(r, n, st, `Alfa ${k.toUpperCase()} : ${Object.entries(o).map(([a, b]) => `${a} ${b}`).join(', ')}`, 'Siteimprove Alfa');
    }

    // DOM rendu et captures, hors dépôt
    writeFileSync(`${HORS}/dom/${nomf}.html`, await page.content());
    await page.screenshot({ path: `${HORS}/captures/${nomf}__haut.jpg`, type: 'jpeg', quality: 70 }).catch(() => {});
    await page.screenshot({ path: `${HORS}/captures/${nomf}.jpg`, type: 'jpeg', quality: 55, fullPage: true, timeout: 30000 }).catch(() => {});

    // 196 : impression réelle, cookies refusés
    if (/^Accueil|^Produit/.test(e.gabarit)) {
      const menu = await page.evaluate(() => [...new Set([...document.querySelectorAll('header nav a, header [role=navigation] a')].map(a => a.innerText.trim()).filter(t => t.length > 3 && t.length < 30))].slice(0, 15));
      const f = `${HORS}/${nomf}.pdf`;
      await page.pdf({ path: f, format: 'A4' });
      spawnSync('pdftoppm', ['-f', '1', '-l', '1', '-r', '45', '-jpeg', f, `${HORS}/captures/${nomf}__impression`]);
      const txt = spawnSync('pdftotext', ['-layout', f, '-'], { encoding: 'utf8' }).stdout || '';
      const presents = menu.filter(m => txt.toLowerCase().includes(m.toLowerCase()));
      if (menu.length) ajoute(r, '196', presents.length > Math.floor(menu.length / 4) ? 'NC' : 'C',
        `${presents.length} libellé(s) du menu d'en-tête sur ${menu.length} dans le PDF imprimé (cookies refusés)${presents.length ? ' : ' + presents.slice(0, 4).join(', ') : ''}`, 'Impression PDF (cookies refusés)');
    }
  } catch (err) {
    r._non_teste = String(err.message).split('\n')[0].slice(0, 140);
    if (/closed|crash|Target/.test(r._non_teste)) { try { await nav.close(); } catch {} nav = await chromium.launch(); }
  }
  try { await ctx.close(); } catch {}
  writeFileSync(fichier, JSON.stringify(res, null, 1));
  console.log(e.service, '|', e.gabarit, '|', r._non_teste || Object.entries(r).filter(([k]) => !k.startsWith('_')).map(([k, l]) => `${k}:${l.map(x => x[0]).join('/')}`).join(' '), r._opquast ? `(opquast : ${r._opquast})` : '');
  await pause(8000);
}
await nav.close(); await req.dispose();
console.log(fichier);
