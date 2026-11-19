// Deuxièmes sources par page, avec les outils déjà installés (lecture seule, aucune saisie, aucun envoi).
//
// Règles d'axe-core et d'IBM Equal Access qui croisent une règle Opquast mais n'étaient pas exploitées (benchmark du
// 12/11), plus deux mesures d'une autre nature que le relevé :
// - 154 : écoute des ouvertures de fenêtres (événement « popup » de Playwright) pendant le chargement ;
// - 196 : impression réelle en PDF (limite constatée le 12/11 : le bandeau cookies, non refusé, recouvre souvent la page
//   imprimée ; résultat à regarder sur le PDF avant de le retenir) (page.pdf) puis extraction du texte par pdftotext (poppler) : les libellés du menu
//   principal ne doivent pas s'y trouver. Le relevé, lui, lisait les styles calculés en émulation impression.
// Statut par outil : échec -> NC ; réussite sans échec -> C ; « à vérifier » seul -> I (ne compte pas comme source) ;
// règle inapplicable -> NA.
//
// Usage : node scripts/sources_page.mjs [--service "Boutique A"]
// Sortie : resultats/sources-AAAA-MM-JJ/pages.json  { site: { url: { regle: [[statut, preuve, outil], …] } } }
import { chromium } from 'playwright';
import { readFileSync, writeFileSync, mkdirSync, existsSync, rmSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const RACINE = new URL('..', import.meta.url).pathname;
const args = process.argv.slice(2);
const seul = args.includes('--service') ? args[args.indexOf('--service') + 1] : null;
const pause = ms => new Promise(ok => setTimeout(ok, ms));
const ecrans = readFileSync(`${RACINE}scripts/ecrans_en_ligne.csv`, 'utf8').trim().split('\n').slice(1).map(l => {
  const [service, gabarit, ...u] = l.split(','); return { service, gabarit, url: u.join(',') };
}).filter(e => !seul || e.service === seul);
const date = new Date().toISOString().slice(0, 10);
const dossier = `${RACINE}resultats/sources-${date}`;
mkdirSync(dossier, { recursive: true });
const fichier = `${dossier}/pages.json`;
const res = existsSync(fichier) ? JSON.parse(readFileSync(fichier, 'utf8')) : {};
const tmp = `${dossier}/.pdf`; mkdirSync(tmp, { recursive: true });

const AXE_OQ = {
  'link-in-text-block': ['140'], blink: ['126'], marquee: ['126'], 'no-autoplay-audio': ['126'], tabindex: ['167'],
  'scrollable-region-focusable': ['166'], 'nested-interactive': ['166'], 'frame-focusable-content': ['166'],
  'document-title': ['103'], 'th-has-data-cells': ['245'], 'td-headers-attr': ['245'], 'meta-refresh': ['172'],
  'button-name': ['159'], 'svg-img-alt': ['159'], 'role-img-alt': ['159'], 'input-image-alt': ['159', '117'],
  'image-alt': ['118'], 'link-name': ['117'],
};
const IBM_OQ = {
  select_options_grouped: ['93'], asciiart_alt_exists: ['14'], emoticons_alt_exists: ['189'],
  style_focus_visible: ['165'], element_tabbable_visible: ['165'], element_tabbable_unobscured: ['165'],
  element_scrollable_tabbable: ['166'], aria_keyboard_handler_exists: ['166'], element_mouseevent_keyboard: ['166'], widget_tabbable_exists: ['166'],
  media_autostart_controllable: ['126'], blink_elem_deprecated: ['126'], marquee_elem_avoid: ['126'],
  table_structure_misuse: ['245'], table_headers_exists: ['245'], page_title_valid: ['103'], meta_refresh_delay: ['172'],
  img_alt_valid: ['118'], a_text_purpose: ['117'],
};

function verdict(o) { return o.echec ? 'NC' : o.reussi ? 'C' : o.a_verifier ? 'I' : 'NA'; }

let nav = await chromium.launch();
for (const e of ecrans) {
  const s = (res[e.service] ??= {});
  if (s[e.url] && !s[e.url]._non_teste) continue;
  const r = (s[e.url] = { _gabarit: e.gabarit });
  let ctx;
  try { ctx = await nav.newContext({ viewport: { width: 1280, height: 900 }, locale: 'fr-FR' }); }
  catch { try { await nav.close(); } catch {} nav = await chromium.launch(); ctx = await nav.newContext({ viewport: { width: 1280, height: 900 }, locale: 'fr-FR' }); }
  const page = await ctx.newPage();
  const fenetres = [];
  page.on('popup', p => fenetres.push(p.url()));
  try {
    const rep = await page.goto(e.url, { waitUntil: 'load', timeout: 45000 });
    if (new URL(page.url()).hostname !== new URL(e.url).hostname) throw new Error('quitte le site (compte client hébergé par Shopify)');
    if (!rep || rep.status() >= 400) throw new Error(`code ${rep ? rep.status() : '?'}`);
    await pause(6000);
    if (/cf-challenge|Just a moment|verify you are human|connexion doit être vérifiée/i.test(await page.title() + ' ' + (await page.evaluate(() => document.body?.innerText.slice(0, 600) || ''))))
      throw new Error('vérification anti-robot affichée : non contournée');
    // capture pleine page, gardée HORS du dépôt (contenu des sites clients), pour la lecture visuelle indépendante
    if (process.env.CAPTURES) {
      mkdirSync(process.env.CAPTURES, { recursive: true });
      const nomf = `${e.service}__${e.gabarit}`.replace(/[^A-Za-z0-9_]+/g, '_').slice(0, 80);
      await page.screenshot({ path: `${process.env.CAPTURES}/${nomf}.jpg`, type: 'jpeg', quality: 60, fullPage: true, timeout: 30000 }).catch(() => {});
      await page.screenshot({ path: `${process.env.CAPTURES}/${nomf}__haut.jpg`, type: 'jpeg', quality: 70, timeout: 30000 }).catch(() => {});
    }
    r['154'] = [[fenetres.length ? 'NC' : 'C', fenetres.length ? `${fenetres.length} fenêtre(s) ouverte(s) au chargement : ${fenetres.join(', ').slice(0, 150)}` : 'Aucune nouvelle fenêtre ouverte pendant le chargement et 6 s après', 'Playwright (événements popup)']];

    // axe-core : règles ciblées, avec réussites et inapplicables
    await page.addScriptTag({ path: `${RACINE}node_modules/axe-core/axe.min.js` });
    const ax = await page.evaluate(async ids => {
      const x = await window.axe.run(document, { runOnly: { type: 'rule', values: ids } });
      const o = {};
      for (const v of x.violations) (o[v.id] ??= { echec: 0, reussi: 0, a_verifier: 0 }).echec += v.nodes.length;
      for (const v of x.passes) (o[v.id] ??= { echec: 0, reussi: 0, a_verifier: 0 }).reussi += v.nodes.length;
      for (const v of x.incomplete) (o[v.id] ??= { echec: 0, reussi: 0, a_verifier: 0 }).a_verifier += v.nodes.length;
      for (const v of x.inapplicable) o[v.id] ??= { echec: 0, reussi: 0, a_verifier: 0 };  // aucun élément concerné : non applicable
      return o;
    }, Object.keys(AXE_OQ));
    const parRegle = {};
    for (const [id, o] of Object.entries(ax)) for (const n of AXE_OQ[id]) (parRegle[n] ??= { axe: [], ibm: [] }).axe.push([id, o]);

    await page.addScriptTag({ path: `${RACINE}node_modules/accessibility-checker-engine/ace.js` });
    const ib = await page.evaluate(async ids => {
      const r = await new window.ace.Checker().check(document, ['IBM_Accessibility']);
      const o = {};
      for (const x of r.results.filter(x => ids.includes(x.ruleId))) {
        const c = (o[x.ruleId] ??= { echec: 0, reussi: 0, a_verifier: 0 });
        if (x.value[1] === 'FAIL') c.echec++; else if (x.value[1] === 'POTENTIAL' || x.value[1] === 'MANUAL') c.a_verifier++; else if (x.value[1] === 'PASS') c.reussi++;
      }
      for (const id of ids) o[id] ??= { echec: 0, reussi: 0, a_verifier: 0 };  // règle sans élément concerné : non applicable
      return o;
    }, Object.keys(IBM_OQ));
    for (const [id, o] of Object.entries(ib)) for (const n of IBM_OQ[id]) (parRegle[n] ??= { axe: [], ibm: [] }).ibm.push([id, o]);
    for (const [n, x] of Object.entries(parRegle)) {
      for (const [outil, l] of [['axe-core', x.axe], ['IBM Equal Access', x.ibm]]) {
        if (!l.length) continue;
        const tot = l.reduce((a, [, o]) => ({ echec: a.echec + o.echec, reussi: a.reussi + o.reussi, a_verifier: a.a_verifier + o.a_verifier }), { echec: 0, reussi: 0, a_verifier: 0 });
        (r[n] ??= []).push([verdict(tot), l.map(([id, o]) => `${id} : ${o.echec} échec(s), ${o.reussi} réussi(s), ${o.a_verifier} à vérifier`).join(' ; '), outil]);
      }
    }

    // 196 : impression réelle, sur l'accueil et la fiche produit
    if (/^Accueil|^Produit/.test(e.gabarit)) {
      const menu = await page.evaluate(() => [...new Set([...document.querySelectorAll('header nav a, nav[aria-label] a, header a[href*="/collections/"]')]
        .map(a => a.innerText.trim()).filter(t => t.length > 3 && t.length < 30))].slice(0, 15));
      const f = `${tmp}/p.pdf`;
      await page.pdf({ path: f, format: 'A4' });
      const txt = spawnSync('pdftotext', ['-layout', f, '-'], { encoding: 'utf8' }).stdout || '';
      const presents = menu.filter(m => txt.toLowerCase().includes(m.toLowerCase()));
      r['196'] = [[!menu.length ? 'I' : presents.length <= Math.floor(menu.length / 4) ? 'C' : 'NC',
        `${presents.length} libellé(s) du menu sur ${menu.length} retrouvé(s) dans le PDF imprimé${presents.length ? ' : ' + presents.slice(0, 5).join(', ') : ''}`, 'Chromium page.pdf + pdftotext']];
    }
  } catch (err) {
    r._non_teste = String(err.message).split('\n')[0].slice(0, 140);
    if (/closed|crash|Target/.test(r._non_teste)) { try { await nav.close(); } catch {} nav = await chromium.launch(); }
  }
  try { await ctx.close(); } catch {}
  writeFileSync(fichier, JSON.stringify(res, null, 1));
  console.log(e.service, '|', e.gabarit, '|', r._non_teste || Object.entries(r).filter(([k]) => !k.startsWith('_')).map(([k, l]) => `${k}:${l.map(x => x[0]).join('/')}`).join(' '));
  await pause(8000);
}
await nav.close();
rmSync(tmp, { recursive: true, force: true });
console.log(fichier);
